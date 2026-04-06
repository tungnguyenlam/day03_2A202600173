"""
Lab runner: baseline chatbot vs ReAct agent, benchmarks, telemetry summary.

Examples (repo root):
  python run_lab.py chatbot --question "What is 2+2?"
  python run_lab.py agent --question "Buy 2 iPhones with WINNER, ship to Hanoi. Unit $1000, 0.4kg each. Total?"
  python run_lab.py compare --question "..."
  python run_lab.py benchmark
  python run_lab.py agent --provider openai
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

import chatbot as baseline_chatbot
from src.agent.agent import ReActAgent
from src.core.provider_factory import create_llm_from_env
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
from src.telemetry.reporting import append_compare_csv, append_experiment_record
from src.agent.dalat_prompts import (
    BASELINE_CHATBOT_SYSTEM_DALAT,
    DALAT_SCENARIO_QUERY_VI,
    build_dalat_system_prompt_v1,
    build_dalat_system_prompt_v2,
)
from src.tools.dalat_travel_tools import get_tool_specs_dalat
from src.tools.ecommerce_tools import get_tool_specs


def _bench_cases() -> list[tuple[str, str]]:
    return [
        (
            "simple_math",
            "What is 17 + 25? Reply with just the number in Final Answer style if you are the agent.",
        ),
        (
            "multi_step_commerce",
            (
                "I want to buy 2 iPhones using coupon code WINNER and ship to Hanoi. "
                "Each iPhone costs $1000 and weighs 0.4 kg. "
                "Use tools for stock/discount/shipping facts, then compute the total I pay "
                "(subtotal after discount + shipping) and give Final Answer with the dollar amount."
            ),
        ),
    ]


def _is_dalat_travel_query(question: str) -> bool:
    q = (question or "").lower()
    keywords = [
        "da lat",
        "dalat",
        "đà lạt",
        "hotel",
        "khách sạn",
        "weather",
        "thời tiết",
        "thoi tiet",
    ]
    return any(k in q for k in keywords)


def run_agent(question: str, provider: str | None, prompt_version: str) -> str:
    llm = create_llm_from_env(provider=provider)
    if _is_dalat_travel_query(question):
        tools = get_tool_specs_dalat()
        if prompt_version == "v1":
            system_override = build_dalat_system_prompt_v1(tools)
            pv = "dalat_v1"
            temp = 0.25
        else:
            system_override = build_dalat_system_prompt_v2(tools)
            pv = "dalat_v2"
            temp = 0.15
        agent = ReActAgent(
            llm,
            tools,
            max_steps=12,
            prompt_version=pv,
            temperature=temp,
            system_prompt_override=system_override,
        )
    else:
        tools = get_tool_specs()
        agent = ReActAgent(llm, tools, max_steps=10, prompt_version=prompt_version)
    return agent.run(question)


def cmd_chatbot(args: argparse.Namespace) -> None:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)
    tracker.reset()
    ans = baseline_chatbot.run_chatbot(args.question, provider=args.provider)
    print(ans)
    logger.log_event("LAB_CHATBOT_DONE", {"summary": tracker.summarize_session()})
    append_experiment_record(
        {
            "event": "LAB_CHATBOT_DONE",
            "mode": "chatbot",
            "provider": args.provider,
            "question": args.question,
            "summary": tracker.summarize_session(),
        }
    )


def cmd_agent(args: argparse.Namespace) -> None:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)
    tracker.reset()
    ans = run_agent(args.question, args.provider, args.prompt_version)
    print(ans)
    logger.log_event(
        "LAB_AGENT_DONE",
        {"summary": tracker.summarize_session(), "prompt_version": args.prompt_version},
    )
    append_experiment_record(
        {
            "event": "LAB_AGENT_DONE",
            "mode": "agent",
            "provider": args.provider,
            "question": args.question,
            "prompt_version": args.prompt_version,
            "summary": tracker.summarize_session(),
        }
    )


def cmd_compare(args: argparse.Namespace) -> None:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)
    print("=== Baseline chatbot (no tools) ===\n")
    tracker.reset()
    b = baseline_chatbot.run_chatbot(args.question, provider=args.provider)
    chat_metrics = tracker.summarize_session()
    print(b)
    print("\n=== ReAct agent (tools) ===\n")
    tracker.reset()
    a = run_agent(args.question, args.provider, args.prompt_version)
    agent_metrics = tracker.summarize_session()
    print(a)
    row = {
        "question": args.question,
        "chatbot_tokens": chat_metrics.get("total_tokens"),
        "agent_tokens": agent_metrics.get("total_tokens"),
        "chatbot_cost_usd": chat_metrics.get("total_cost_estimate_usd"),
        "agent_cost_usd": agent_metrics.get("total_cost_estimate_usd"),
    }
    print("\n=== Comparison (see logs/ for traces) ===")
    print(json.dumps(row, indent=2))
    logger.log_event("LAB_COMPARE", row)
    append_experiment_record(
        {
            "event": "LAB_COMPARE",
            "mode": "compare",
            "provider": args.provider,
            "prompt_version": args.prompt_version,
            "question": args.question,
            "comparison": row,
            "chatbot_metrics": chat_metrics,
            "agent_metrics": agent_metrics,
        }
    )
    append_compare_csv(
        {
            "scenario": "compare",
            "provider": args.provider or os.getenv("DEFAULT_PROVIDER") or "openai",
            "prompt_version": args.prompt_version,
            "question": args.question,
            "chatbot_requests": chat_metrics.get("requests"),
            "chatbot_tokens": chat_metrics.get("total_tokens"),
            "chatbot_cost_usd": chat_metrics.get("total_cost_estimate_usd"),
            "chatbot_latency_p50_ms": chat_metrics.get("latency_ms_p50"),
            "chatbot_latency_p99_ms": chat_metrics.get("latency_ms_p99"),
            "agent_requests": agent_metrics.get("requests"),
            "agent_tokens": agent_metrics.get("total_tokens"),
            "agent_cost_usd": agent_metrics.get("total_cost_estimate_usd"),
            "agent_latency_p50_ms": agent_metrics.get("latency_ms_p50"),
            "agent_latency_p99_ms": agent_metrics.get("latency_ms_p99"),
        }
    )


def cmd_dalat_compare(args: argparse.Namespace) -> None:
    """
    Baseline chatbot vs ReAct Agent v1 (minimal prompt) vs v2 (strict JSON + workflow).
    Uses OpenAI by default when DEFAULT_PROVIDER is unset; set OPENAI_API_KEY in .env.
    """
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)
    q = args.question or DALAT_SCENARIO_QUERY_VI
    prov = args.provider or os.getenv("DEFAULT_PROVIDER") or "openai"

    print("=== Baseline chatbot (no tools, Đà Lạt-aware system prompt) ===\n")
    tracker.reset()
    b = baseline_chatbot.run_chatbot(q, provider=prov, system_prompt=BASELINE_CHATBOT_SYSTEM_DALAT)
    m_chat = tracker.summarize_session()
    print(b)

    tools = get_tool_specs_dalat()
    llm = create_llm_from_env(provider=prov, model=args.model)

    print("\n=== Agent v1 — minimal ReAct instructions + key=value Actions ===\n")
    tracker.reset()
    agent_v1 = ReActAgent(
        llm,
        tools,
        max_steps=12,
        prompt_version="dalat_v1",
        temperature=0.25,
        system_prompt_override=build_dalat_system_prompt_v1(tools),
    )
    a1 = agent_v1.run(q)
    m_v1 = tracker.summarize_session()
    print(a1)

    print("\n=== Agent v2 — stricter prompt, JSON Actions, tool-order guardrails ===\n")
    tracker.reset()
    agent_v2 = ReActAgent(
        llm,
        tools,
        max_steps=12,
        prompt_version="dalat_v2",
        temperature=0.15,
        system_prompt_override=build_dalat_system_prompt_v2(tools),
    )
    a2 = agent_v2.run(q)
    m_v2 = tracker.summarize_session()
    print(a2)

    row = {
        "question": q,
        "provider": prov,
        "chatbot_tokens": m_chat.get("total_tokens"),
        "agent_v1_tokens": m_v1.get("total_tokens"),
        "agent_v2_tokens": m_v2.get("total_tokens"),
        "chatbot_cost_usd": m_chat.get("total_cost_estimate_usd"),
        "agent_v1_cost_usd": m_v1.get("total_cost_estimate_usd"),
        "agent_v2_cost_usd": m_v2.get("total_cost_estimate_usd"),
        "chatbot_requests": m_chat.get("requests"),
        "agent_v1_requests": m_v1.get("requests"),
        "agent_v2_requests": m_v2.get("requests"),
    }
    print("\n=== Token / cost summary (see logs/ for full traces) ===")
    print(json.dumps(row, indent=2, ensure_ascii=False))
    logger.log_event("LAB_DALAT_COMPARE", row)
    append_experiment_record(
        {
            "event": "LAB_DALAT_COMPARE",
            "mode": "dalat-compare",
            "provider": prov,
            "question": q,
            "comparison": row,
            "chatbot_metrics": m_chat,
            "agent_v1_metrics": m_v1,
            "agent_v2_metrics": m_v2,
        }
    )
    append_compare_csv(
        {
            "scenario": "dalat-compare",
            "provider": prov,
            "prompt_version": "v1_vs_v2",
            "question": q,
            "chatbot_requests": m_chat.get("requests"),
            "chatbot_tokens": m_chat.get("total_tokens"),
            "chatbot_cost_usd": m_chat.get("total_cost_estimate_usd"),
            "chatbot_latency_p50_ms": m_chat.get("latency_ms_p50"),
            "chatbot_latency_p99_ms": m_chat.get("latency_ms_p99"),
            "agent_v1_requests": m_v1.get("requests"),
            "agent_v1_tokens": m_v1.get("total_tokens"),
            "agent_v1_cost_usd": m_v1.get("total_cost_estimate_usd"),
            "agent_v1_latency_p50_ms": m_v1.get("latency_ms_p50"),
            "agent_v1_latency_p99_ms": m_v1.get("latency_ms_p99"),
            "agent_v2_requests": m_v2.get("requests"),
            "agent_v2_tokens": m_v2.get("total_tokens"),
            "agent_v2_cost_usd": m_v2.get("total_cost_estimate_usd"),
            "agent_v2_latency_p50_ms": m_v2.get("latency_ms_p50"),
            "agent_v2_latency_p99_ms": m_v2.get("latency_ms_p99"),
        }
    )


def cmd_benchmark(args: argparse.Namespace) -> None:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)
    tracker.reset()
    results = []
    for name, q in _bench_cases():
        print(f"\n--- Case: {name} ---\n")
        if args.mode in ("chatbot", "both"):
            tracker.reset()
            print("[chatbot]")
            print(baseline_chatbot.run_chatbot(q, provider=args.provider))
            results.append({"case": name, "mode": "chatbot", "metrics": tracker.summarize_session()})
        if args.mode in ("agent", "both"):
            tracker.reset()
            print("[agent]")
            print(run_agent(q, args.provider, args.prompt_version))
            results.append({"case": name, "mode": "agent", "metrics": tracker.summarize_session()})
    logger.log_event("LAB_BENCHMARK", {"runs": results})
    append_experiment_record(
        {
            "event": "LAB_BENCHMARK",
            "mode": "benchmark",
            "provider": args.provider,
            "prompt_version": args.prompt_version,
            "runs": results,
        }
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Lab 3 runner: chatbot vs ReAct agent")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("chatbot", help="Single baseline LLM call")
    pc.add_argument("--question", "-q", required=True)
    pc.add_argument("--provider", default=None, help="Override DEFAULT_PROVIDER for this run")
    pc.set_defaults(func=cmd_chatbot)

    pa = sub.add_parser("agent", help="ReAct agent with tools")
    pa.add_argument("--question", "-q", required=True)
    pa.add_argument("--provider", default=None)
    pa.add_argument("--prompt-version", choices=("v1", "v2"), default="v2")
    pa.set_defaults(func=cmd_agent)

    pc2 = sub.add_parser("compare", help="Run chatbot then agent on the same question")
    pc2.add_argument("--question", "-q", required=True)
    pc2.add_argument("--provider", default=None)
    pc2.add_argument("--prompt-version", choices=("v1", "v2"), default="v2")
    pc2.set_defaults(func=cmd_compare)

    pb = sub.add_parser("benchmark", help="Run scripted cases")
    pb.add_argument("--mode", choices=("chatbot", "agent", "both"), default="both")
    pb.add_argument("--provider", default=None)
    pb.add_argument("--prompt-version", choices=("v1", "v2"), default="v2")
    pb.set_defaults(func=cmd_benchmark)

    pd = sub.add_parser(
        "dalat-compare",
        help="Đà Lạt scenario: chatbot vs Agent v1 vs Agent v2 (3 tools; OpenAI recommended)",
    )
    pd.add_argument(
        "--question",
        "-q",
        default=None,
        help="User message (default: scripted Đà Lạt weekend scenario with explicit dates)",
    )
    pd.add_argument("--provider", default=None, help="e.g. openai (default if .env unset)")
    pd.add_argument("--model", default=None, help="Override model name for the provider")
    pd.set_defaults(func=cmd_dalat_compare)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
