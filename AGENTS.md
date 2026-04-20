# AGENTS.md

## Purpose
This repository builds and evaluates a ReAct agent against a baseline chatbot for Lab 3.
The target is not just a working demo. The target is measurable improvement with traceable failures, telemetry evidence, and report-ready artifacts.

## Primary System We Are Building
- Baseline chatbot: one model call, no tools.
- ReAct agent: Thought -> Action -> Observation loop with strict parsing and tool execution.
- Evaluation modes: chatbot, agent, compare, benchmark, dalat-compare.

Core files:
- run_lab.py
- src/agent/agent.py
- src/agent/dalat_prompts.py
- src/tools/ecommerce_tools.py
- src/tools/dalat_travel_tools.py
- src/tools/dalat_dummy_data_tool.py
- src/telemetry/logger.py
- src/telemetry/metrics.py
- src/telemetry/reporting.py

## Behavioral Contract For The Agent
The agent must:
1. Output either Action: tool_name(...) or Final Answer: ... after Thought:.
2. Never fabricate Observation; observation is system-appended.
3. Use only tools listed in current tool inventory.
4. End within max_steps and avoid loops.
5. Be grounded in tool observations for factual tasks.

Common failure codes to monitor:
- PARSE_ERROR
- HALLUCINATION_TOOL
- JSON_PARSER_ERROR
- TOOL_ARG_MISMATCH
- TOOL_RUNTIME_ERROR
- TIMEOUT

## Tooling Strategy
### E-commerce tools
Use when reasoning chain is stock -> discount -> shipping -> final total.
- check_stock
- get_discount
- calc_shipping

### Da Lat travel tools
Use when reasoning chain is weather -> hotel search -> review check -> recommendation.
- get_weather
- search_hotels
- get_hotel_reviews
- get_dummy_travel_data (single-call mock snapshot for testing and demos)

## Provider Strategy
Supported providers in provider factory:
- openai
- google or gemini
- local (llama-cpp GGUF)
- huggingface or hf (Transformers local model)

For Hugging Face local run, default model:
- Qwen/Qwen2.5-0.5B-Instruct

Recommended .env knobs:
- DEFAULT_PROVIDER
- DEFAULT_MODEL
- HF_MODEL_ID
- HF_MAX_NEW_TOKENS
- LOCAL_MODEL_PATH

## Iterative Workflow (Required)
Always work in this loop for each requirement item:
1. Pick one rubric item.
2. Implement minimal code change.
3. Run focused test or command.
4. Run scenario evaluation command.
5. Capture evidence from logs.
6. Update report section with measured result.
7. Move to next rubric item.

Do not batch many unverified changes across multiple rubric items.

## Execution Commands
Install and setup:
- pip install -r requirements.txt
- cp .env.example .env

Run modes:
- python run_lab.py chatbot --question "..."
- python run_lab.py agent --question "..."
- python run_lab.py compare --question "..."
- python run_lab.py benchmark
- python run_lab.py dalat-compare

Useful options:
- --provider openai|gemini|local|huggingface
- --prompt-version v1|v2

## Evidence And Artifacts
After each iteration, collect these artifacts:
- logs/sessions/session-*.log
- logs/experiments.jsonl
- logs/compare_summary.csv

Use them to fill:
- report/group_report/GROUP_REPORT_C4.md
- report/group_report/GROUP_REPORT_DRAFT.md
- report/individual_reports/*.md

## Scoring-Aligned Definition Of Done
A change is done only when all are true:
1. Code compiles and targeted tests pass.
2. At least one run command confirms behavior.
3. Failure and success traces are documented when applicable.
4. Metrics (tokens, latency, cost) are captured when relevant.
5. Report section for that rubric item is updated with evidence.

## Practical Guardrails
- Keep tools deterministic and atomic.
- Prefer strict argument formats in prompts and examples.
- Keep prompts and parser expectations in sync.
- Log every meaningful failure with explicit code.
- Keep max_steps bounded to control cost and runaway loops.

## Suggested Next Iteration Order
1. Chatbot baseline evidence
2. Agent v1 evidence
3. Agent v2 improvements
4. Tool design evolution narrative
5. Trace quality section with 1 success + 2 failures
6. Evaluation and comparison tables
7. Flowchart and insights
8. Bonus items (extra monitoring, failure handling, ablations)
