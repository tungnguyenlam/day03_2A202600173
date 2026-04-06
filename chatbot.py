"""
Baseline chatbot: one LLM call, no tools — highlights limits on multi-step factual tasks.
Run from repo root: python chatbot.py "your question"
"""
from __future__ import annotations

import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

from src.core.provider_factory import create_llm_from_env
from src.telemetry.metrics import tracker

BASELINE_SYSTEM = """You are a helpful assistant. Answer in one reply.
You do NOT have access to tools, databases, or live APIs.
If the user asks for stock, coupons, or shipping fees that require external data you do not have,
reason transparently and clearly state what you are guessing versus what you cannot verify."""


def run_chatbot(
    user_message: str,
    provider: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> str:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)
    llm = create_llm_from_env(provider=provider)
    sys_p = system_prompt if system_prompt is not None else BASELINE_SYSTEM
    out = llm.generate(user_message, system_prompt=sys_p, temperature=0.3)
    tracker.track_request(
        out.get("provider", "unknown"),
        llm.model_name,
        out.get("usage") or {},
        int(out.get("latency_ms") or 0),
    )
    return (out.get("content") or "").strip()


def main() -> None:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)
    q = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else input("You: ").strip()
    if not q:
        print("Provide a question as an argument or when prompted.")
        return
    print(run_chatbot(q))


if __name__ == "__main__":
    main()
