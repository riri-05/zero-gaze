"""OpenRouter model gateway and resilient fallback cascade."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import time
from typing import Any, TypeVar
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from zero_gaze.core.errors import ExtractionError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_PRIMARY_MODEL = "deepseek/deepseek-v4-flash-0731:free"
DEFAULT_REASONING_MODEL = "qwen/qwen3.8-27b:free"
DEFAULT_FAST_MODEL = "nvidia/nemotron-3.5-lightning:free"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


def load_env_file(filepath: str = ".env") -> dict[str, str]:
    """Parse local .env file if environment variables are not already in os.environ."""
    env: dict[str, str] = {}
    path = Path(filepath)
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip().strip("\"'")
    return env


class ModelGateway:
    """Manages LLM client initialization and fallback routing over OpenRouter."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        models_cascade: list[str] | None = None,
        max_retries_per_model: int = 2,
        backoff_seconds: float = 2.0,
    ) -> None:
        env = load_env_file()
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY") or env.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ExtractionError("OPENROUTER_API_KEY is required but not configured.")

        self.base_url = (
            base_url
            or os.environ.get("OPENROUTER_BASE_URL")
            or env.get("OPENROUTER_BASE_URL")
            or DEFAULT_BASE_URL
        )

        primary = (
            os.environ.get("PRIMARY_MODEL")
            or env.get("PRIMARY_MODEL")
            or DEFAULT_PRIMARY_MODEL
        )
        reasoning = (
            os.environ.get("REASONING_MODEL")
            or env.get("REASONING_MODEL")
            or DEFAULT_REASONING_MODEL
        )
        fast = (
            os.environ.get("FAST_MODEL")
            or env.get("FAST_MODEL")
            or DEFAULT_FAST_MODEL
        )

        self.models_cascade = models_cascade or [primary, reasoning, fast]
        self.max_retries_per_model = max_retries_per_model
        self.backoff_seconds = backoff_seconds

    def get_chat_model(self, model_name: str, temperature: float = 0.0) -> ChatOpenAI:
        """Create a configured ChatOpenAI client pointing to OpenRouter."""
        return ChatOpenAI(
            model=model_name,
            openai_api_key=self.api_key,
            openai_api_base=self.base_url,
            default_headers={
                "HTTP-Referer": "https://github.com/riri-05/zero-gaze",
                "X-Title": "Zero Gaze ML Replication Agent",
            },
            temperature=temperature,
            timeout=90.0,
            max_retries=1,
        )

    def invoke_structured(
        self,
        schema: type[T],
        prompt: str,
        system_instruction: str | None = None,
    ) -> T:
        """Invoke LLM with Pydantic structured output, cascading across fallback models on error."""
        last_exception: Exception | None = None

        messages: list[dict[str, str]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        for model_idx, model_name in enumerate(self.models_cascade):
            for attempt in range(1, self.max_retries_per_model + 1):
                try:
                    logger.info(
                        "Invoking structured model '%s' (cascade %d/%d, attempt %d/%d)...",
                        model_name,
                        model_idx + 1,
                        len(self.models_cascade),
                        attempt,
                        self.max_retries_per_model,
                    )
                    llm = self.get_chat_model(model_name)
                    structured_llm = llm.with_structured_output(schema)
                    result = structured_llm.invoke(messages)
                    if isinstance(result, schema):
                        return result
                    if isinstance(result, dict):
                        return schema.model_validate(result)
                    logger.warning(
                        "Model '%s' returned unrecognized type: %s. Retrying...",
                        model_name,
                        type(result),
                    )
                except Exception as err:
                    last_exception = err
                    err_msg = str(err)
                    logger.warning(
                        "Error on model '%s' attempt %d: %s",
                        model_name,
                        attempt,
                        err_msg,
                    )
                    if attempt < self.max_retries_per_model:
                        time.sleep(self.backoff_seconds * attempt)

            logger.warning(
                "Exhausted retries for model '%s'. Cascading to next model...",
                model_name,
            )

        raise ExtractionError(
            f"All models in cascade failed to generate structured output: {last_exception}",
            details={"cascade": self.models_cascade, "last_error": str(last_exception)},
        ) from last_exception
