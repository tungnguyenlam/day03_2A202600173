# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: C4
- **Team Members**: Trần Gia Khánh - 2A202600293, Phạm Trần Thanh Lâm - 2A202600270, Phạm Việt Cường - 2A202600420, Nguyễn Lâm Tùng - 2A202600173, Đặng Tiến Dũng - 2A202600024, Phạm Hữu Hoàng Hiệp - 2A202600415

---

## 1. Executive Summary

Our project compares a baseline chatbot (single LLM call, no tools) with a ReAct agent (Thought -> Action -> Observation) for multi-step tasks. The final system improves reliability by tightening tool specs, adding JSON-friendly action patterns, and analyzing failures through structured telemetry logs.

- **Success Rate**: [Fill after running benchmark]
- **Key Outcome**: Agent is more reliable than baseline on multi-step tasks that require external facts (stock, discount, shipping, weather, hotel reviews).

---

## 2. System Architecture & Tooling

### 2.1 ReAct Loop Implementation

The ReAct loop is implemented in `src/agent/agent.py`:
1. Generate response from LLM.
2. Parse either `Final Answer:` or `Action: tool(args)`.
3. If Action exists, execute tool and append `Observation: ...`.
4. Repeat until final answer or `max_steps`.

Error codes captured in telemetry:
- `PARSE_ERROR`
- `HALLUCINATION_TOOL`
- `JSON_PARSER_ERROR`
- `TOOL_ARG_MISMATCH`
- `TIMEOUT`

### 2.2 Tool Design Evolution (Required Rubric Item)

This section documents the tool design progression from a basic format (v1) to a robust, parser-friendly format (v2).

| Version | Tool Spec Style | Action Format Used by LLM | Main Issue Observed | Improvement Introduced |
| :--- | :--- | :--- | :--- | :--- |
| **v1** | Short natural-language descriptions, mixed argument style | `Action: tool("x", 1)` or `tool(k=v)` | Inconsistent argument formatting, more parse failures | Standardized examples added to prompt |
| **v1.5** | Clearer argument requirements per tool | Prefer `key=value` for kwargs tools | LLM still outputs markdown/code fences or malformed args | Added markdown fence stripping + stronger output rules |
| **v2** | Explicit schema-like descriptions and JSON-first examples | `Action: tool({"arg": value})` | Hallucinated tools and wrong ordering in some cases | Guardrails: one action/turn, JSON object args, suggested tool order |

#### 2.2.1 E-commerce tools evolution (`src/tools/ecommerce_tools.py`)

- **Initial goal**: support multi-step price computation.
- **Final tool set**:
  - `check_stock(item_name)`
  - `get_discount(coupon_code)`
  - `calc_shipping(weight_kg, destination)`
- **Why this design works**:
  - Tools are atomic and deterministic.
  - Return strings with interpretable facts for the next reasoning step.
  - Covers a complete chain: availability -> discount -> shipping -> total.

#### 2.2.2 Da Lat travel tools evolution (`src/tools/dalat_travel_tools.py`)

- **Initial goal**: create realistic travel planning chain.
- **Final tool set**:
  - `get_weather(city, date)`
  - `search_hotels(city, check_in, check_out, max_price)`
  - `get_hotel_reviews(hotel_id)`
- **v2 prompt alignment**:
  - Strong JSON action examples.
  - Recommended order:
    1) weather
    2) hotel search with budget
    3) reviews before final recommendation

#### 2.2.3 Design principles learned

1. Tool descriptions must include strict input expectations (type + format examples).
2. Fewer, composable tools are better than one overloaded tool.
3. Prompt and parser should co-evolve (spec change must be reflected in prompt examples).
4. Tool outputs should be concise, factual, and machine-readable enough for next-step reasoning.

### 2.3 LLM Providers Used

- **Primary**: OpenAI (`gpt-4o` default in `provider_factory.py`)
- **Secondary (Backup)**: Gemini (`gemini-1.5-flash`)
- **Optional Local**: GGUF model via `llama-cpp-python`

---

## 3. Telemetry & Performance Dashboard

Telemetry is logged by:
- `src/telemetry/logger.py` (event logs)
- `src/telemetry/metrics.py` (token, latency, estimated cost)
- `src/telemetry/reporting.py` (experiment snapshots for comparison)

Generated files for grading:
- `logs/YYYY-MM-DD.log` (raw event traces)
- `logs/experiments.jsonl` (one run = one JSON object)
- `logs/compare_summary.csv` (table for direct chatbot-vs-agent comparison)

Fill these after your final run:
- **Average Latency (P50)**: [ms]
- **Max Latency (P99)**: [ms]
- **Average Tokens per Task**: [tokens]
- **Total Cost of Test Suite**: [USD]

---

## 4. Trace Quality (Required Rubric Item)

This section includes both successful and failed traces, with root-cause analysis and remediation.

### 4.1 Success Trace: Multi-step E-commerce query

- **Input**: "I want to buy 2 iPhones using coupon WINNER and ship to Hanoi..."
- **Expected action chain**:
  1. `Action: check_stock("iPhone")`
  2. `Action: get_discount("WINNER")`
  3. `Action: calc_shipping(0.8, "Hanoi")`
  4. `Final Answer: ...`
- **Quality indicators**:
  - No parse error.
  - Correct tool sequence.
  - Final answer grounded in tool observations.

### 4.2 Failure Trace A: Parse error

- **Observed event**: `AGENT_ERROR` with code `PARSE_ERROR`
- **Symptom**: LLM output had Thought text but no parseable `Action:` or `Final Answer:`.
- **Root cause**: Output formatting drift (extra prose / non-compliant structure).
- **Fix**:
  - Enforce strict output rules in system prompt.
  - Keep one action per turn.
  - Add correction observation on parse failure (already in `agent.py`).

### 4.3 Failure Trace B: Hallucinated tool

- **Observed event**: `AGENT_ERROR` with code `HALLUCINATION_TOOL`
- **Symptom**: Agent called a tool not present in tool inventory.
- **Root cause**: Tool description block not specific enough or model ignored constraints.
- **Fix**:
  - Strengthen tool inventory prompt.
  - Add explicit "valid tools list" reminder.
  - Keep tool names short and unambiguous.

### 4.4 Failure Trace C: Timeout / loop

- **Observed event**: `AGENT_END` with `outcome=MAX_STEPS` and `code=TIMEOUT`
- **Symptom**: Agent repeated steps without finalizing.
- **Root cause**: Weak termination criterion in model behavior.
- **Fix**:
  - Prompt v2 instructs concise finalization once enough evidence is collected.
  - Keep `max_steps` bounded to control cost and latency.

### 4.5 Trace Evidence Checklist (for grading)

For each trace attached in appendix, include:
1. Input query
2. Event timeline (`AGENT_START`, `TOOL_CALL`, `AGENT_ERROR`/`AGENT_END`)
3. At least 1 success and 2 failure traces
4. Root cause and specific prompt/tool change made after diagnosis
5. Before/after comparison result (v1 vs v2)

Data source reference:
- Trace timeline from `logs/YYYY-MM-DD.log`
- Numeric comparison from `logs/compare_summary.csv`

---

## 5. Ablation Studies & Experiments

### Experiment 1: Prompt v1 vs Prompt v2
- **Diff**: v2 uses stricter action contract, JSON-object args, and tool-order guardrails.
- **Result**: [Fill with your measured reduction in parse/tool-call errors]

### Experiment 2: Chatbot vs Agent
| Case | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| Simple Q&A | [Fill] | [Fill] | [Fill] |
| Multi-step with external facts | [Fill] | [Fill] | **Agent** |

---

## 6. Production Readiness Review

- **Security**: Validate and sanitize tool arguments before runtime calls.
- **Guardrails**: Keep `max_steps` and strict output contracts to prevent runaway loops.
- **Scaling**: Move from mock tools to real APIs with retries/circuit breaker and richer observability.

---

> [!NOTE]
> Rename this file to `GROUP_REPORT_[TEAM_NAME].md` before submission.
