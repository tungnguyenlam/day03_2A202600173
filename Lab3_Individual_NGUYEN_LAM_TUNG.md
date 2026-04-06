# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Tung Nguyen
- **Student ID**: 2A202600173
- **Date**: 2026-04-06

---

## I. Technical Contribution (15 Points)

I implemented and tested a dedicated OpenAI ReAct stock agent with live tool calls and telemetry-driven analysis.

- **Modules Implemented**:
  - `stock_tung_agent.py`
- **Key Features Added**:
  - ReAct loop implementation (`Thought -> Action -> Observation -> Final Answer`) in a standalone `StockReActAgent` class.
  - `get_stock_price(symbol)` tool:
    - Primary source: Stooq CSV endpoint.
    - Fallback source: Yahoo Finance public quote endpoint.
  - `convert_currency(amount, from_currency, to_currency)` tool via exchangerate.host.
  - Strict OpenAI provider usage (as required) using API key from `.env`.
  - Telemetry integration with existing `tracker` and `logger` (`LLM_METRIC`, `AGENT_STEP`, `AGENT_FINAL`, `STOCK_TUNG_AGENT_DONE`).
  - CLI interface for reproducible runs:
    - `python stock_tung_agent.py -q "What is the latest AAPL stock price?"`

- **Code Highlights**:
  - Robust action parsing (`Action: tool_name(args...)`) with quoted-argument handling.
  - Graceful tool fallback strategy (Stooq -> Yahoo).
  - Key-loading hardening: fallback to `dotenv_values(".env")` when shell environment variable is empty.

- **How it connects to ReAct loop**:
  - LLM decides tool usage in `Action` format.
  - Tool output is inserted back as `Observation`.
  - LLM uses observation to produce `Final Answer`.
  - Loop is capped with `max_steps` to prevent infinite loops.

- **Executed Test Runs (real runs)**:
  - `python stock_tung_agent.py -q "What is the latest AAPL stock price?"`
  - `python stock_tung_agent.py -q "Check stock price for ZZZZ1234"`
  - `python stock_tung_agent.py -q "Get AAPL price and convert to VND"`

- **Where logging is stored**:
  - Structured logger implementation: `src/telemetry/logger.py`
  - Runtime log file for this session: `logs/2026-04-06.log`

---

## II. Debugging Case Study (10 Points)

- **Case Chosen**: Multi-step request failed at currency conversion.

- **User Prompt**:
  - `Get AAPL price and convert to VND`

- **Trace Evidence from `logs/2026-04-06.log`**:
  - Step 1 (`AGENT_STEP`):
    - Model action: `get_stock_price("AAPL")`
    - Observation: `AAPL latest close: 255.92 USD (date 2026-04-02, time 22:00:18).`
  - Step 2 (`AGENT_STEP`):
    - Model action: `convert_currency(255.92, "USD", "VND")`
    - Observation: `Could not convert 255.92 USD to VND.`
  - Step 3 (`AGENT_FINAL`):
    - Final answer: `The latest AAPL stock price is 255.92 USD. However, I couldn't convert it to VND at this time.`

- **Additional Root-Cause Evidence (manual API probe)**:
  - Request to exchangerate.host returned:
    - `{"success": false, "error": {"code": 101, "type": "missing_access_key", ...}}`

- **Diagnosis**:
  - The `convert_currency` tool assumes free anonymous access.
  - The provider currently requires an access key, so the API returns unsuccessful payload and no numeric `result`.
  - The agent behaves correctly (does not hallucinate a converted value), but user intent is only partially fulfilled.

- **Fixes Implemented During Development**:
  - Dependency/runtime fixes:
    - installed `python-dotenv`, `openai`, `requests`.
    - removed transitive local-model import dependency from this script path.
  - Reliability fix:
    - strengthened OpenAI key loading using `.env` fallback.

- **Planned Improvement for this failure**:
  - Add `EXCHANGE_API_KEY` support and pass it to the currency endpoint.
  - Add secondary conversion provider fallback when primary conversion API fails.
  - Return structured error categories (auth error / rate limit / network) to improve auto-retry policy.

- **Outcome**:
  - For stock lookup, the agent is successful and grounded by tool output.
  - For currency conversion, failure is reproducible, diagnosed, and documented with trace evidence.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**:
  - ReAct improved reliability because tool calls grounded the answer in external market data instead of pure model memory.
2. **Reliability Trade-off**:
  - ReAct can still fail when external tools fail (example: conversion API access-key requirement).
  - For simple Q&A, a direct chatbot is faster and cheaper due to single call and no tool overhead.
3. **Role of Observation**:
  - Observation is the critical feedback signal that allows the model to revise and finalize accurately.
  - In this project, it prevented hallucination: the agent explicitly reported conversion failure instead of inventing a VND value.

---

## IV. Future Improvements (5 Points)

- **Scalability**:
  - Add async tool execution and cache recent quotes to reduce repeated API calls.
- **Safety/Robustness**:
  - Add ticker validation against exchange symbol lists and guardrails for invalid actions.
  - Add explicit tool health checks at startup and fail-fast messages when a dependency API requires credentials.
- **Performance/Cost**:
  - Use a smaller model for tool-selection step and reserve larger model only for complex synthesis.
- **Production Path**:
  - Add retries with circuit-breaker logic for unstable market APIs and integrate monitoring dashboards for SLA tracking.
  - Persist per-tool success rate metrics to compare tool reliability over time.

---

> Final artifact submitted as: `report/individual_reports/REPORT_TUNG_NGUYEN.md`
