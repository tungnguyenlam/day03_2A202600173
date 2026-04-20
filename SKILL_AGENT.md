# SKILL_AGENT.md

## Purpose
Reusable prompt skill for strict ReAct tool-calling in this lab.
Use this when you want consistent tool usage, fewer parse errors, and grounded answers.

## Core Contract
Always output exactly one of these per turn:
1. `Thought: ...` then `Action: tool_name(...)`
2. `Thought: ...` then `Final Answer: ...`

Never output `Observation:` yourself.
Only call tools that exist in the provided tool list.

## Output Rules
- Keep exactly these headers: `Thought:`, `Action:`, `Final Answer:`
- One action per turn
- No markdown code fences
- Use JSON-object arguments for kwargs tools when possible

## Action Patterns
### E-commerce tools
- `Action: check_stock("iPhone")`
- `Action: get_discount("WINNER")`
- `Action: calc_shipping(0.8, "Hanoi")`

Recommended chain:
1. stock check
2. discount lookup
3. shipping cost
4. final total

### Da Lat travel tools
- `Action: get_weather({"city": "Da Lat", "date": "2026-04-12"})`
- `Action: search_hotels({"city": "Da Lat", "check_in": "2026-04-12", "check_out": "2026-04-13", "max_price": 800000})`
- `Action: get_hotel_reviews({"hotel_id": "ngoc_lan_hotel"})`
- `Action: get_dummy_travel_data({"city": "Da Lat", "date": "2026-04-12", "max_price": 800000})`

Recommended chain:
1. weather first
2. hotel search with budget filter
3. review check
4. concise final recommendation

## Failure Recovery
If previous turn indicates parse error:
- Next turn must strictly follow `Thought:` + `Action:` or `Final Answer:`
- Do not add extra prose

If a tool is unknown or arguments fail:
- Correct the action using known tool names
- Retry with valid argument format

## Final Answer Quality
- Must be grounded in observations
- For factual queries: include concrete numbers from tool outputs
- For travel: include hotel suggestion, price, reason, weather summary, and clothing tip
- Keep concise
