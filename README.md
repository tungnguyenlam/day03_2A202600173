# Lab 3: Chatbot vs ReAct Agent (GROUP C4)

Welcome to Phase 3 of the Agentic AI course! This lab focuses on moving from a simple LLM Chatbot to a sophisticated **ReAct Agent** with industry-standard monitoring.

## 🚀 Getting Started

### 1. Setup Environment
Copy the `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Directory Structure
- `src/tools/`: Extension point for your custom tools.

## 🏠 Running with Local Models (CPU)

If you don't want to use OpenAI or Gemini, you can run open-source models (like Phi-3) directly on your CPU using `llama-cpp-python`.

## 🤗 Running with Hugging Face Qwen (Local)

You can also run `Qwen/Qwen2.5-0.5B-Instruct` locally through Transformers.

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Update `.env`
```env
DEFAULT_PROVIDER=huggingface
HF_MODEL_ID=Qwen/Qwen2.5-0.5B-Instruct
HF_MAX_NEW_TOKENS=512
```

### 3. Run chatbot or agent
```bash
python run_lab.py chatbot --question "Xin chao"
python run_lab.py agent --question "Buy 2 iPhones with WINNER, ship to Hanoi. Unit $1000, 0.4kg each. Total?"
```

Notes:
- First run downloads model weights from Hugging Face and can take time.
- CPU inference is supported; CUDA will be used automatically if available.

### 1. Download the Model
Download the **Phi-3-mini-4k-instruct-q4.gguf** (approx 2.2GB) from Hugging Face:
- [Phi-3-mini-4k-instruct-GGUF](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf)
- Direct Download: [phi-3-mini-4k-instruct-q4.gguf](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf)

### 2. Place Model in Project
Create a `models/` folder in the root and move the downloaded `.gguf` file there.

### 3. Update `.env`
Change your `DEFAULT_PROVIDER` and set the path:
```env
DEFAULT_PROVIDER=local
LOCAL_MODEL_PATH=./models/Phi-3-mini-4k-instruct-q4.gguf
```

## 🎯 Lab Objectives

1.  **Baseline Chatbot**: Observe the limitations of a standard LLM when faced with multi-step reasoning.
2.  **ReAct Loop**: Implement the `Thought-Action-Observation` cycle in `src/agent/agent.py`.
3.  **Provider Switching**: Swap between OpenAI and Gemini seamlessly using the `LLMProvider` interface.
4.  **Failure Analysis**: Use the structured logs in `logs/` to identify why the agent fails (hallucinations, parsing errors).
5.  **Grading & Bonus**: Follow the [SCORING.md](file:///Users/tindt/personal/ai-thuc-chien/day03-lab-agent/SCORING.md) to maximize your points and explore bonus metrics.

## 🛠️ How to Use This Baseline
The code is designed as a **Production Prototype**. It includes:
- **Telemetry**: Every action is logged in JSON format for later analysis.
- **Robust Provider Pattern**: Easily extendable to any LLM API.
- **Clean Skeletons**: Focus on the logic that matters—the agent's reasoning process.

## 📊 Comparison Logs (for report scoring)

Run `./run_lab_tests.sh` to run all test prompts.
When you run `compare`, `dalat-compare`, or `benchmark`, the lab now writes:

- `logs/sessions/session-*.log`: low-level event traces, one file per run/session
- `logs/experiments.jsonl`: one structured record per run
- `logs/compare_summary.csv`: table-ready metrics (tokens, latency, cost) for chatbot vs agent

This makes it easy to fill **Tool Design Evolution**, **Trace Quality**, and **Evaluation & Analysis** sections in the group report.

---

*Happy Coding! Let's build agents that actually work.*
