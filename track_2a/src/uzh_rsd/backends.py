"""Generation backends. Both return the same :class:`Generation` record.

* :class:`OpenAICompatibleBackend` — the judge path: ``LLM_NAME``,
  ``LLM_BASE_URL``, ``LLM_API_KEY`` (OpenAI-compatible chat completions,
  stdlib only, one attempt per call, key never recorded).
* :class:`TransformersBackend` — the HF batch-GPU path used for the measured
  runs: local weights, loaded once, greedy decoding. Imports torch/transformers
  lazily so the rest of the package stays stdlib-only.

Decoding is greedy in both (``temperature=0`` / ``do_sample=False``), matching
the upstream ``predict_llama.py`` baseline script.
"""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass

from .apertus_smoke import _chat_url, safe_endpoint


@dataclass
class Generation:
    text: str | None
    error: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    finish_reason: str | None = None
    latency_s: float | None = None
    token_count_source: str = "unavailable"

    def as_dict(self) -> dict:
        return asdict(self)


class OpenAICompatibleBackend:
    kind = "openai-compatible"

    def __init__(self, base_url: str, model: str, api_key: str, *, timeout_s: float = 600.0,
                 opener: Callable[..., object] = urllib.request.urlopen, clock: Callable[[], float] = time.monotonic):
        self._url = _chat_url(base_url)
        self._endpoint = safe_endpoint(base_url)
        self._model = model
        self._key = api_key
        self._timeout = timeout_s
        self._opener = opener
        self._clock = clock

    def describe(self) -> dict:
        return {"backend": self.kind, "endpoint": self._endpoint, "model": self._model, "timeout_s": self._timeout, "max_attempts": 1}

    def generate(self, prompt: str, max_new_tokens: int) -> Generation:
        body = json.dumps({
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_new_tokens,
            "temperature": 0.0,
        }).encode()
        request = urllib.request.Request(self._url, data=body, method="POST", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {self._key}"})
        started = self._clock()
        try:
            with self._opener(request, timeout=self._timeout) as response:  # type: ignore[operator]
                raw = response.read()
        except urllib.error.HTTPError as error:
            return Generation(None, f"HTTP {error.code}", latency_s=round(self._clock() - started, 3))
        except (TimeoutError, socket.timeout):
            return Generation(None, "timeout", latency_s=round(self._clock() - started, 3))
        except (urllib.error.URLError, OSError) as error:
            reason = getattr(error, "reason", error)
            return Generation(None, f"transport error: {type(reason).__name__}", latency_s=round(self._clock() - started, 3))
        latency = round(self._clock() - started, 3)
        try:
            payload = json.loads(raw)
            choice = payload["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("content is not a string")
        except (ValueError, KeyError, IndexError, TypeError):
            return Generation(None, "malformed chat completion response", latency_s=latency)
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        return Generation(
            content,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            finish_reason=choice.get("finish_reason"),
            latency_s=latency,
            token_count_source="endpoint usage" if usage else "unavailable",
        )


class TransformersBackend:
    """Verified HF Jobs pattern: explicit ``.to("cuda")`` (no accelerate in the image)."""

    kind = "transformers"

    def __init__(self, model_id: str, revision: str, *, device: str = "cuda"):
        import torch
        import transformers
        from transformers import AutoModelForMultimodalLM, AutoProcessor

        self._torch = torch
        self.model_id, self.revision, self.device = model_id, revision, device
        started = time.monotonic()
        self.processor = AutoProcessor.from_pretrained(model_id, revision=revision)
        self.model = AutoModelForMultimodalLM.from_pretrained(model_id, revision=revision, dtype="auto").to(device).eval()
        self.load_s = round(time.monotonic() - started, 1)
        eos = self.model.generation_config.eos_token_id
        self._eos = set(eos if isinstance(eos, list) else [eos]) - {None}
        self._content_format = self._select_content_format()
        self._info = {
            "backend": self.kind,
            "model": model_id,
            "revision": revision,
            "dtype": str(next(self.model.parameters()).dtype),
            "device": torch.cuda.get_device_name(0) if device == "cuda" else device,
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "cuda": torch.version.cuda,
            "model_load_s": self.load_s,
            "chat_template_kwargs": {"enable_thinking": False},
            "message_content_format": self._content_format,
            "decoding": {"do_sample": False},
        }

    def _messages(self, prompt: str, content_format: str | None = None) -> list[dict]:
        content_format = content_format or self._content_format
        content = [{"type": "text", "text": prompt}] if content_format == "blocks" else prompt
        return [{"role": "user", "content": content}]

    def _select_content_format(self) -> str:
        """Some processors silently drop plain-string content; verify before use."""
        probe = "Probe sentence: Grüezi, 30 Tage / 60 jours."
        for content_format in ("blocks", "string"):
            try:
                rendered = self.processor.apply_chat_template(
                    self._messages(probe, content_format), add_generation_prompt=True, tokenize=False, enable_thinking=False)
            except Exception:
                continue
            if probe in rendered:
                return content_format
        raise RuntimeError("chat template drops the user prompt in both content formats")

    def describe(self) -> dict:
        return dict(self._info)

    def generate(self, prompt: str, max_new_tokens: int) -> Generation:
        torch = self._torch
        started = time.monotonic()
        try:
            inputs = self.processor.apply_chat_template(
                self._messages(prompt),
                add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt", enable_thinking=False,
            ).to(self.device)
            prompt_tokens = int(inputs["input_ids"].shape[-1])
            with torch.inference_mode():
                output = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
            generated = output[0, prompt_tokens:]
            text = self.processor.decode(generated, skip_special_tokens=True)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            return Generation(None, "cuda out of memory", latency_s=round(time.monotonic() - started, 3))
        except Exception as error:  # recorded, never retried
            return Generation(None, f"{type(error).__name__}: {str(error)[:300]}", latency_s=round(time.monotonic() - started, 3))
        ids = generated.tolist()
        hit_eos = bool(ids) and ids[-1] in self._eos
        finish = "stop" if hit_eos or len(ids) < max_new_tokens else "length"
        return Generation(
            text,
            prompt_tokens=prompt_tokens,
            completion_tokens=len(ids),
            finish_reason=finish,
            latency_s=round(time.monotonic() - started, 3),
            token_count_source="model tokenizer",
        )
