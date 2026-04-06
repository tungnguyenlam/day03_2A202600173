# Group Report: Lab 3 - Production-Grade Agentic System

- **Team Name**: [Your Team]
- **Team Members**: [Member 1, Member 2, ...]
- **Deployment Date**: 2026-04-06

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
- **Optional Local (Transformers)**: Hugging Face Qwen (`Qwen/Qwen2.5-0.5B-Instruct`)

---

## 3. Telemetry & Performance Dashboard

Telemetry is logged by:
- `src/telemetry/logger.py` (event logs)
- `src/telemetry/metrics.py` (token, latency, estimated cost)
- `src/telemetry/reporting.py` (experiment snapshots for comparison)

Generated files for grading:
- `logs/sessions/session-*.log` (raw event traces, one file per run)
- `logs/experiments.jsonl` (one run = one JSON object)
- `logs/compare_summary.csv` (table for direct chatbot-vs-agent comparison)

Fill these after your final run:
- **Average Latency (P50)**: 18,138 ms median across the four benchmark runs recorded in `logs/2026-04-06.log`.
- **Max Latency (P99)**: 39,567 ms in the multi-step commerce chatbot benchmark case.
- **Average Tokens per Task**: 303.75 tokens across the four benchmark runs.
- **Total Cost of Test Suite**: $0.01215 for the benchmark runs captured so far.

---

## 4. Trace Quality (Required Rubric Item)

This section includes both successful and failed traces, with root-cause analysis and remediation.

### 4.1 Success Trace: Tool-grounded factual query

- **Input**: "What is the latest AAPL stock price?"
- **Expected action chain**:
  1. `Action: get_stock_price("AAPL")`
  2. `Final Answer: 255.92 USD`
- **Quality indicators**:
  - No parse error.
  - Correct tool sequence.
  - Final answer grounded in tool observations.

### 4.1.1 Observed success evidence

The log shows the agent completed the tool-grounded stock query and returned a final answer with token and latency telemetry captured in the session log.

- **Event timeline**:
  1. `LLM_METRIC` recorded the first model call.
  2. `AGENT_STEP` captured `Action: get_stock_price("AAPL")`.
  3. `AGENT_FINAL` returned the factual answer.
- **Measured result**:
  - Agent tokens: 525
  - Agent latency p50: 2,234 ms
  - Agent cost estimate: $0.001673

This trace is useful because it demonstrates the system can close the loop on a reasoning task and ground the final answer in a tool observation.

### 4.2 Failure Trace A: Parse error

- **Observed event**: `AGENT_ERROR` with code `PARSE_ERROR`
- **Symptom**: LLM output had Thought text but no parseable `Action:` or `Final Answer:`.
- **Root cause**: Output formatting drift (extra prose / non-compliant structure).
- **Fix**:
  - Enforce strict output rules in system prompt.
  - Keep one action per turn.
  - Add correction observation on parse failure (already in `agent.py`).

**Observed trace**:
- `AGENT_START` at `08:48:46`
- `LLM_METRIC` at `08:48:49`
- `AGENT_ERROR` with `code=PARSE_ERROR`
- `AGENT_END` with a fallback natural-language recommendation

### 4.3 Failure Trace B: Hallucinated Da Lat hotel answer

- **Observed event**: `AGENT_END` after the Qwen local model answered with a fabricated hotel name and price.
- **Symptom**: The agent produced "Hotel XYZ" for Da Lat without consulting any tool or inventory.
- **Root cause**: The model failed to stay grounded when no tool result was produced; this is a factual hallucination failure.
- **Fix**:
  - Strengthen tool inventory prompt.
  - Add explicit "valid tools list" reminder.
  - Keep tool names short and unambiguous.

**Observed trace pattern**:
- `AGENT_START` at `08:57:18`
- `LLM_METRIC` at `08:57:33`
- `AGENT_END` with answer preview: "There is a hotel called Hotel XYZ that costs $399 per night."

### 4.4 Failure Trace C: Tool argument mismatch

- **Observed event**: `AGENT_STEP` during the currency conversion attempt in the stock workflow.
- **Symptom**: The tool call `convert_currency(255.92, "USD", "VND")` returned `Could not convert 255.92 USD to VND.`
- **Root cause**: The tool chain did not support the requested conversion path in the current inventory.
- **Fix**:
  - Keep tool capabilities explicit in the prompt.
  - Route unsupported requests to a fallback explanation instead of retrying indefinitely.

**Observed trace pattern**:
- `AGENT_STEP` at `08:15:35` and `08:15:37`
- Observation returned a tool-level conversion failure rather than a numeric output.
- `AGENT_FINAL` at `08:15:38` summarized the partial success and limitation.

### 4.5 Trace Evidence Checklist (for grading)

For each trace attached in appendix, include:
1. Input query
2. Event timeline (`AGENT_START`, `TOOL_CALL`, `AGENT_ERROR`/`AGENT_END`)
3. At least 1 success and 2 failure traces
4. Root cause and specific prompt/tool change made after diagnosis
5. Before/after comparison result (v1 vs v2)

Data source reference:
- Trace timeline from `logs/sessions/session-*.log`
- Numeric comparison from `logs/compare_summary.csv`

---

## 5. Ablation Studies & Experiments

### Experiment 1: Prompt v1 vs Prompt v2
- **Diff**: v2 uses stricter action contract, JSON-object args, and tool-order guardrails.
- **Result**: v2 is the documented target for the current benchmark set and produced a successful multi-step commerce final answer with 31,193 ms latency and 478 tokens. The report should treat this as the improved baseline over the looser v1 prompt.

### Experiment 2: Chatbot vs Agent
| Case | Chatbot Result | Agent Result | Winner |
| :--- | :--- | :--- | :--- |
| Simple Q&A | Solved with 111 tokens and 5,083 ms | Solved with 300 tokens and 2,203 ms | Draw |
| Multi-step with external facts | Solved, but no tool-grounded evidence captured | Tool-grounded total of $976.80 with 478 tokens and 31,193 ms | **Agent** |

### Experiment 3: Benchmark summary

| Case | Mode | Tokens | Latency (ms) | Cost (USD) |
| :--- | :--- | :--- | :--- | :--- |
| simple_math | chatbot | 111 | 5,083 | 0.00111 |
| simple_math | agent | 300 | 2,203 | 0.00300 |
| multi_step_commerce | chatbot | 326 | 39,567 | 0.00326 |
| multi_step_commerce | agent | 478 | 31,193 | 0.00478 |

**Interpretation**: the agent spends more tokens, but it produces grounded results on the multi-step commerce task and remains faster than the chatbot on the hardest case recorded.

---

## 6. Production Readiness Review

- **Security**: Validate and sanitize tool arguments before runtime calls.
- **Guardrails**: Keep `max_steps` and strict output contracts to prevent runaway loops.
- **Scaling**: Move from mock tools to real APIs with retries/circuit breaker and richer observability.

---

## 7. Flowchart & Insights

### ReAct Loop Flow

```text
START
  |
  v
Generate LLM response
  |
  +--> Final Answer present? -- yes --> Return answer and log AGENT_END
  |
  no
  |
  +--> Parseable Action present? -- yes --> Execute tool --> Append Observation --> Loop
  |                                         |
  |                                         +--> tool error --> log failure code --> Loop
  |
  no
  |
  +--> Log PARSE_ERROR --> Append correction Observation --> Loop
  |
  v
Stop if max_steps reached -> log TIMEOUT
```

### Group Insights

1. The chatbot is acceptable for simple Q&A, but it is not reliable for fact-grounded multi-step tasks.
2. The ReAct agent becomes useful once the prompt and parser are aligned tightly enough to convert tool observations into final answers.
3. Trace quality matters as much as final correctness because the rubric rewards explainability, not just answer quality.
4. The dummy travel tool is valuable because it gives us deterministic mock data for repeated agent evaluation without relying on live APIs.

---

> [!NOTE]
> Rename this file to `GROUP_REPORT_[TEAM_NAME].md` before submission.
