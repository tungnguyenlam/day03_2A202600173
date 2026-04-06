"""
OpenAI-based ReAct stock agent for Lab 3.

Examples:
  python stock_tung_agent.py -q "What is the latest AAPL stock price?"
  python stock_tung_agent.py -q "Get TSLA stock price and convert it to VND"
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import dotenv_values, load_dotenv

from src.core.openai_provider import OpenAIProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


def _strip_markdown_fences(text: str) -> str:
    t = text.strip()
    if not t.startswith("```"):
        return t
    lines = t.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _split_csv_args(blob: str) -> List[str]:
    blob = blob.strip()
    if not blob:
        return []
    parts: List[str] = []
    cur: List[str] = []
    in_quote: Optional[str] = None
    i = 0
    while i < len(blob):
        ch = blob[i]
        if in_quote:
            cur.append(ch)
            if ch == in_quote and (i == 0 or blob[i - 1] != "\\"):
                in_quote = None
            i += 1
            continue
        if ch in "\"'":
            in_quote = ch
            cur.append(ch)
            i += 1
            continue
        if ch == ",":
            parts.append("".join(cur).strip())
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    if cur:
        parts.append("".join(cur).strip())
    return parts


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def _normalize_arg_tokens(raw_parts: List[str]) -> List[Any]:
    out: List[Any] = []
    for p in raw_parts:
        p = p.strip()
        if not p:
            continue
        p = _strip_quotes(p)
        try:
            if "." in p:
                out.append(float(p))
            else:
                out.append(int(p))
            continue
        except ValueError:
            out.append(p)
    return out


def _parse_final_answer(text: str) -> Optional[str]:
    m = re.search(r"Final\s*Answer\s*:\s*([^\n]+)", text, flags=re.IGNORECASE)
    if not m:
        return None
    return m.group(1).strip()


def _parse_action(text: str) -> Optional[Tuple[str, str]]:
    m = re.search(r"Action\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)", text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    return m.group(1).strip(), m.group(2).strip()


class StockReActAgent:
    def __init__(self, llm: Any, tools: List[Dict[str, Any]], max_steps: int = 8):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self._tool_index = {t["name"]: t for t in tools}

    def run(self, question: str, system_prompt: str) -> str:
        transcript = f"User: {question}"
        for step in range(1, self.max_steps + 1):
            out = self.llm.generate(transcript, system_prompt=system_prompt, temperature=0.1)
            tracker.track_request(
                out.get("provider", "unknown"),
                getattr(self.llm, "model_name", "unknown"),
                out.get("usage") or {},
                int(out.get("latency_ms") or 0),
            )
            llm_text = _strip_markdown_fences((out.get("content") or "").strip())

            final_ans = _parse_final_answer(llm_text)
            if final_ans:
                logger.log_event("AGENT_FINAL", {"step": step, "answer": final_ans})
                return final_ans

            action = _parse_action(llm_text)
            if not action:
                msg = "I could not parse an action/final answer from the model output."
                logger.log_event("AGENT_ERROR", {"code": "PARSE_ERROR", "step": step, "raw": llm_text[:500]})
                return msg

            tool_name, args_blob = action
            spec = self._tool_index.get(tool_name)
            if not spec:
                observation = f"Error: unknown tool '{tool_name}'."
            else:
                try:
                    args = _normalize_arg_tokens(_split_csv_args(args_blob))
                    observation = str(spec["run"](args))
                except Exception as e:
                    observation = f"Error executing {tool_name}: {e}"

            logger.log_event(
                "AGENT_STEP",
                {
                    "step": step,
                    "model_output": llm_text,
                    "tool": tool_name,
                    "tool_args": args_blob,
                    "observation": observation,
                },
            )
            transcript += (
                f"\n\nStep {step}\n"
                f"Assistant: {llm_text}\n"
                f"Observation: {observation}"
            )

        return "I reached max steps before producing a final answer."


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper().replace("$", "")


def _fetch_stooq_quote(symbol: str) -> str:
    """Fetch latest daily quote from Stooq CSV endpoint (free, no API key)."""
    ticker = f"{symbol.lower()}.us"
    url = f"https://stooq.com/q/l/?s={ticker}&f=sd2t2ohlcv&h&e=csv"
    r = requests.get(url, timeout=12)
    r.raise_for_status()
    lines = [ln.strip() for ln in r.text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return ""

    header = [x.strip().lower() for x in lines[0].split(",")]
    values = [x.strip() for x in lines[1].split(",")]
    row = dict(zip(header, values))

    close_v = row.get("close", "N/D")
    date_v = row.get("date", "N/D")
    time_v = row.get("time", "N/D")
    if close_v in ("N/D", "", "-"):
        return ""
    return f"{symbol} latest close: {close_v} USD (date {date_v}, time {time_v})."


def get_stock_price(symbol: str) -> str:
    """Get latest stock quote. Falls back to Yahoo Finance public endpoint."""
    sym = _normalize_symbol(symbol)
    if not sym:
        return "Error: symbol is empty. Example: AAPL"

    try:
        stooq_msg = _fetch_stooq_quote(sym)
        if stooq_msg:
            return stooq_msg
    except requests.RequestException:
        pass

    # Fallback: Yahoo quote endpoint (public market data)
    try:
        y_url = "https://query1.finance.yahoo.com/v7/finance/quote"
        r = requests.get(y_url, params={"symbols": sym}, timeout=12)
        r.raise_for_status()
        data = r.json()
        result = ((data or {}).get("quoteResponse") or {}).get("result") or []
        if not result:
            return f"No quote found for symbol '{sym}'."

        q = result[0]
        price = q.get("regularMarketPrice")
        currency = q.get("currency", "USD")
        ts = q.get("regularMarketTime")
        dt_txt = "unknown time"
        if isinstance(ts, (int, float)):
            dt_txt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        if price is None:
            return f"Quote is unavailable for symbol '{sym}'."
        return f"{sym} latest price: {price} {currency} (as of {dt_txt})."
    except requests.RequestException as e:
        return f"Error fetching quote for '{sym}': {e}"


def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert currency using exchangerate.host public API."""
    fr = from_currency.strip().upper()
    to = to_currency.strip().upper()
    amt = float(amount)

    if not fr or not to:
        return "Error: from_currency and to_currency are required."

    url = "https://api.exchangerate.host/convert"
    try:
        r = requests.get(url, params={"from": fr, "to": to, "amount": amt}, timeout=12)
        r.raise_for_status()
        data = r.json() or {}
        result = data.get("result")
        info = data.get("info") or {}
        rate = info.get("rate")
        if result is None:
            return f"Could not convert {amt} {fr} to {to}."
        if rate is None:
            return f"{amt:.4f} {fr} = {float(result):.4f} {to}."
        return f"{amt:.4f} {fr} = {float(result):.4f} {to} (rate: {float(rate):.6f})."
    except requests.RequestException as e:
        return f"Error converting currency: {e}"


def _run_get_stock_price(args: List[Any]) -> str:
    if not args:
        return "Error: get_stock_price requires symbol, e.g. get_stock_price(\"AAPL\")."
    return get_stock_price(str(args[0]))


def _run_convert_currency(args: List[Any]) -> str:
    if len(args) < 3:
        return (
            "Error: convert_currency requires (amount, from_currency, to_currency), "
            "e.g. convert_currency(100, \"USD\", \"VND\")."
        )
    return convert_currency(float(args[0]), str(args[1]), str(args[2]))


def get_stock_tool_specs() -> List[Dict[str, Any]]:
    return [
        {
            "name": "get_stock_price",
            "description": (
                "Get latest stock quote for one symbol. "
                "Args: symbol string (examples: AAPL, TSLA, MSFT). "
                "Returns latest market price/close and timestamp."
            ),
            "run": _run_get_stock_price,
        },
        {
            "name": "convert_currency",
            "description": (
                "Convert a numeric amount between currencies. "
                "Args: amount (number), from_currency (string), to_currency (string). "
                "Example: convert_currency(100, \"USD\", \"VND\")."
            ),
            "run": _run_convert_currency,
        },
    ]


def build_stock_system_prompt(tools: List[Dict[str, Any]]) -> str:
    tool_lines = "\n".join(f"- {t['name']}: {t['description']}" for t in tools)
    return f"""You are StockTungAgent, a ReAct assistant for stock lookup tasks.

Available tools:
{tool_lines}

Rules:
- Use format exactly: Thought:, then either Action: or Final Answer:.
- Do not write Observation: by yourself.
- Action format: tool_name(arg1, arg2, ...). Use quotes for strings.
- If user asks for conversion, call convert_currency after getting stock price.
- If a symbol is unclear, ask a concise clarification in Final Answer.
- Final Answer must be concise and include the symbol and currency.
"""


def run_stock_agent(question: str, model: str | None = None, max_steps: int = 8) -> str:
    load_dotenv()
    env_vals = dotenv_values(".env")
    api_key = os.getenv("OPENAI_API_KEY") or env_vals.get("OPENAI_API_KEY")

    # User explicitly requested OpenAI API from .env.
    llm = OpenAIProvider(
        model_name=model or os.getenv("DEFAULT_MODEL", "gpt-4o"),
        api_key=api_key,
    )
    tools = get_stock_tool_specs()
    system_prompt = build_stock_system_prompt(tools)
    agent = StockReActAgent(llm=llm, tools=tools, max_steps=max_steps)

    tracker.reset()
    answer = agent.run(question, system_prompt=system_prompt)
    logger.log_event(
        "STOCK_TUNG_AGENT_DONE",
        {
            "question": question,
            "model": llm.model_name,
            "summary": tracker.summarize_session(),
        },
    )
    return answer


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="OpenAI ReAct stock price agent")
    p.add_argument("--question", "-q", required=True, help="User question for the stock agent")
    p.add_argument("--model", default=os.getenv("DEFAULT_MODEL", "gpt-4o"), help="OpenAI model name")
    p.add_argument("--max-steps", type=int, default=8, help="Maximum ReAct loop steps")
    return p


def main() -> None:
    args = build_parser().parse_args()
    print(run_stock_agent(args.question, model=args.model, max_steps=args.max_steps))


if __name__ == "__main__":
    main()
