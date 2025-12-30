"""Ollama model client using local/remote Ollama HTTP API."""

import os
import logging
from typing import List, Dict, Any, Optional
import requests

from .base import BaseModelClient, ModelResponse
from ..utils.error_handler import safe_model_call
from ..utils.exceptions import ModelAPIError, ModelTimeoutError

logger = logging.getLogger(__name__)


class OllamaClient(BaseModelClient):
    """Client for Ollama models via HTTP API."""

    def __init__(
        self,
        host: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.base = f"{self.host}/api"
        self.default_model = default_model or os.getenv("OLLAMA_MODEL")

        logger.info("Initialized OllamaClient with host=%s, model=%s", self.host, self.default_model)

    def _post(self, endpoint: str, payload: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
        url = f"{self.base}{endpoint}"
        try:
            r = requests.post(url, json=payload, timeout=timeout, stream=True)
            r.raise_for_status()

            # Try to decode as a single JSON document first
            try:
                return r.json()
            except Exception:
                # Fallback: Ollama may return line-delimited JSON (NDJSON) or streaming chunks.
                # Collect non-empty lines and parse each as JSON, returning the last parsed object.
                import json as _json

                parsed = []
                for raw in r.iter_lines(decode_unicode=True):
                    if not raw:
                        continue
                    line = raw.strip()
                    try:
                        parsed_obj = _json.loads(line)
                        parsed.append(parsed_obj)
                    except Exception:
                        # Non-JSON line, skip
                        continue

                if parsed:
                    # Return all parsed chunks so caller can assemble content
                    return {"_ndjson_parsed": parsed}

                # If nothing parsed, return full text under a key
                text = r.text
                return {"text": text}
        except requests.exceptions.Timeout as e:
            raise ModelTimeoutError(f"Ollama request timeout: {e}")
        except requests.exceptions.RequestException as e:
            logger.error("Ollama API request failed: %s", e)
            raise ModelAPIError(f"Ollama API request failed: {e}")

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> ModelResponse:
        model = model or self.default_model
        if not model:
            raise ValueError("No Ollama model specified. Set OLLAMA_MODEL or pass model parameter.")

        # Convert messages to a prompt if Ollama endpoint expects prompt text
        # Prefer 'messages' if API accepts chat format; we'll attempt to send messages as-is,
        # and fall back to joining into a single prompt.
        payload = {"model": model}

        # Many Ollama deployments use 'prompt' string; build prompt from messages
        prompt_parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            prompt_parts.append(f"{role}: {content}")
        payload["prompt"] = "\n".join(prompt_parts)
        payload["options"] = {"temperature": temperature}
        if max_tokens is not None:
            payload["options"]["max_tokens"] = max_tokens
        payload["options"].update(kwargs.get("options", {}))

        logger.debug("Calling Ollama chat_completion model=%s", model)

        def _call():
            resp = self._post("/generate", payload)
            logger.debug("Ollama raw response: %s", resp)

            # Assemble content from possible fields and from NDJSON parsed chunks
            content_parts = []

            def _extract_from_obj(obj):
                parts = []
                if not isinstance(obj, dict):
                    return parts
                # Common keys used by different Ollama responses
                if "response" in obj and obj.get("response"):
                    parts.append(obj.get("response"))
                if "text" in obj and obj.get("text"):
                    parts.append(obj.get("text"))
                if "content" in obj and obj.get("content"):
                    parts.append(obj.get("content"))
                if "generated" in obj:
                    gen = obj.get("generated")
                    if isinstance(gen, list):
                        for g in gen:
                            if isinstance(g, dict):
                                parts.extend(_extract_from_obj(g))
                            else:
                                parts.append(str(g))
                    elif gen:
                        parts.append(str(gen))
                if "choices" in obj:
                    choices = obj.get("choices") or []
                    for c in choices:
                        if isinstance(c, dict):
                            if c.get("text"):
                                parts.append(c.get("text"))
                            elif isinstance(c.get("message"), dict) and c.get("message").get("content"):
                                parts.append(c.get("message").get("content"))
                return parts

            if isinstance(resp, dict) and "_ndjson_parsed" in resp:
                for chunk in resp.get("_ndjson_parsed", []):
                    content_parts.extend(_extract_from_obj(chunk))
            else:
                content_parts.extend(_extract_from_obj(resp))

            # If caller provided raw text under 'text', include it
            if isinstance(resp, dict) and resp.get("text"):
                content_parts.append(resp.get("text"))

            content = "".join([str(p) for p in content_parts if p])

            return ModelResponse(content=content, model=model, usage=None)

        return safe_model_call(_call, max_retries=2, retry_delay=1.0)

    def multimodal_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        # For multimodal, embed image references into prompt or use API-supported input field
        model = model or self.default_model
        if not model:
            raise ValueError("No Ollama model specified. Set OLLAMA_MODEL or pass model parameter.")

        # Build prompt similar to chat_completion
        prompt_parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            # content may be a list with image entries
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") in ("image_url", "input_image"):
                        url = item.get("image_url") or item.get("image_url", {}).get("url")
                        prompt_parts.append(f"[IMAGE:{url}]")
                    else:
                        prompt_parts.append(str(item))
            else:
                prompt_parts.append(str(content))

        payload = {"model": model, "prompt": "\n".join(prompt_parts), "options": {"temperature": temperature}}
        if max_tokens is not None:
            payload["options"]["max_tokens"] = max_tokens
        payload["options"].update(kwargs.get("options", {}))

        def _call():
            resp = self._post("/generate", payload)
            # parse similar to chat_completion
            content = ""
            if isinstance(resp, dict):
                content = resp.get("content") or resp.get("generated") or ""
            return ModelResponse(content=str(content), model=model, usage=None)

        return safe_model_call(_call, max_retries=2, retry_delay=1.0)
