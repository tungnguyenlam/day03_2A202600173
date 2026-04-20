import time
import os
from typing import Any, Dict, Generator, List, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from src.core.llm_provider import LLMProvider


class HuggingFaceProvider(LLMProvider):
    """
    LLM Provider for local Hugging Face causal language models.
    Default model is Qwen/Qwen2.5-0.5B-Instruct.
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-0.5B-Instruct",
        max_new_tokens: int = 512,
        device: Optional[str] = None,
    ):
        super().__init__(model_name=model_name)
        self.max_new_tokens = max_new_tokens
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.device_info = {
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "hip_version": getattr(torch.version, "hip", None),
        }

        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name, dtype=dtype)
        if self.device != "cpu":
            self.model.to(self.device)
        if self.tokenizer.pad_token_id is None and self.tokenizer.eos_token_id is not None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def _apply_stop_sequences(self, text: str, stop: Optional[List[str]]) -> str:
        if not stop:
            return text
        cut_positions = [text.find(s) for s in stop if s and text.find(s) >= 0]
        if not cut_positions:
            return text
        return text[: min(cut_positions)]

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        stop: Optional[List[str]] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        chat_text = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False,
        )
        model_inputs = self.tokenizer(chat_text, return_tensors="pt")
        input_ids = model_inputs["input_ids"].to(self.device)
        attention_mask = model_inputs.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(self.device)

        gen_kwargs: Dict[str, Any] = {
            "max_new_tokens": self.max_new_tokens,
            "pad_token_id": self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
            "do_sample": temperature is not None and float(temperature) > 0,
        }
        if temperature is not None and float(temperature) > 0:
            gen_kwargs["temperature"] = float(temperature)

        with torch.no_grad():
            if attention_mask is not None:
                output_ids = self.model.generate(input_ids=input_ids, attention_mask=attention_mask, **gen_kwargs)
            else:
                output_ids = self.model.generate(input_ids=input_ids, **gen_kwargs)

        generated_ids = output_ids[0][input_ids.shape[-1] :]
        content = self.tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        content = self._apply_stop_sequences(content, stop)

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        usage = {
            "prompt_tokens": int(input_ids.shape[-1]),
            "completion_tokens": int(generated_ids.shape[-1]),
            "total_tokens": int(input_ids.shape[-1] + generated_ids.shape[-1]),
        }

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "huggingface",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        # Simple fallback streaming: generate once, then yield token-like chunks.
        out = self.generate(prompt=prompt, system_prompt=system_prompt)
        text = out.get("content") or ""
        for part in text.split(" "):
            if part:
                yield part + " "
