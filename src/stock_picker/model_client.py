import os
from typing import Any, Dict, List, Optional, Union

from crewai import LLM
from crewai.llms.base_llm import BaseLLM
from dotenv import load_dotenv

from .constants import (
    DEFAULT_OPENCODE_GO_MODEL,
    DEFAULT_OPENROUTER_MANAGER_MODEL,
    DEFAULT_OPENROUTER_MODEL,
    OPENCODE_GO_ANTHROPIC_BASE_URL,
    OPENCODE_GO_OPENAI_BASE_URL,
    OPENROUTER_BASE_URL,
)

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _strip_known_prefix(model: str, prefixes: tuple[str, ...]) -> str:
    for prefix in prefixes:
        if model.startswith(prefix):
            return model.removeprefix(prefix)
    return model


def _openrouter_model(model: str) -> str:
    model = _strip_known_prefix(model, ("openrouter/",))
    return f"openrouter/{model}"


def _opencode_go_model(model: str) -> str:
    return _strip_known_prefix(model, ("opencode-go/", "openai/", "anthropic/"))


class OpenCodeGoAutoLLM(BaseLLM):
    _protocol_cache: dict[str, str] = {}

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        temperature: Optional[float] = None,
        timeout: Optional[Union[float, int]] = None,
        api_style: str = "auto",
    ) -> None:
        model = _opencode_go_model(model)
        super().__init__(model=f"opencode-go/{model}", temperature=temperature)
        self._model_id = model
        self._api_style = api_style.strip().lower()
        if self._api_style not in {"auto", "openai", "anthropic"}:
            raise ValueError("OPENCODE_GO_API_STYLE must be auto, openai, or anthropic")

        self._openai_llm = LLM(
            model=f"openai/{model}",
            api_key=api_key,
            api_base=OPENCODE_GO_OPENAI_BASE_URL,
            temperature=temperature,
            timeout=timeout,
        )
        self._anthropic_llm = LLM(
            model=f"anthropic/{model}",
            api_key=api_key,
            api_base=OPENCODE_GO_ANTHROPIC_BASE_URL,
            temperature=temperature,
            timeout=timeout,
        )
        self._active_protocol = self._initial_protocol()

    def _initial_protocol(self) -> str:
        if self._api_style != "auto":
            return self._api_style
        if self._model_id in self._protocol_cache:
            return self._protocol_cache[self._model_id]
        if self._model_id.startswith("minimax-"):
            return "anthropic"
        return "openai"

    def _client_for(self, protocol: str) -> LLM:
        return self._anthropic_llm if protocol == "anthropic" else self._openai_llm

    def _alternate_protocol(self) -> str:
        return "anthropic" if self._active_protocol == "openai" else "openai"

    def call(
        self,
        messages: Union[str, List[Dict[str, str]]],
        tools: Optional[List[dict]] = None,
        callbacks: Optional[List[Any]] = None,
        available_functions: Optional[Dict[str, Any]] = None,
        from_task: Optional[Any] = None,
        from_agent: Optional[Any] = None,
    ) -> Union[str, Any]:
        call_args = {
            "messages": messages,
            "tools": tools,
            "callbacks": callbacks,
            "available_functions": available_functions,
            "from_task": from_task,
            "from_agent": from_agent,
        }
        try:
            result = self._client_for(self._active_protocol).call(**call_args)
            self._protocol_cache[self._model_id] = self._active_protocol
            return result
        except Exception as first_error:
            if self._api_style != "auto":
                raise
            first_protocol = self._active_protocol
            self._active_protocol = self._alternate_protocol()
            try:
                result = self._client_for(self._active_protocol).call(**call_args)
                self._protocol_cache[self._model_id] = self._active_protocol
                return result
            except Exception as second_error:
                raise RuntimeError(
                    f"OpenCode Go model '{self._model_id}' failed with both "
                    f"{first_protocol} and {self._active_protocol} API styles. "
                    f"First error: {first_error}"
                ) from second_error

    def supports_stop_words(self) -> bool:
        return self._client_for(self._active_protocol).supports_stop_words()

    def get_context_window_size(self) -> int:
        return self._client_for(self._active_protocol).get_context_window_size()


def create_llm(
    *,
    temperature: Optional[float] = 0.7,
    manager: bool = False,
    timeout: Optional[Union[float, int]] = None,
) -> BaseLLM:
    if _env_bool("USE_OPENROUTER", default=False):
        env_name = "OPENROUTER_MANAGER_MODEL" if manager else "OPENROUTER_MODEL"
        default_model = (
            DEFAULT_OPENROUTER_MANAGER_MODEL if manager else DEFAULT_OPENROUTER_MODEL
        )
        return LLM(
            model=_openrouter_model(os.getenv(env_name, default_model)),
            api_key=_env_required("OPENROUTER_API_KEY"),
            api_base=os.getenv("OPENROUTER_BASE_URL", OPENROUTER_BASE_URL),
            temperature=temperature,
            timeout=timeout,
        )

    return OpenCodeGoAutoLLM(
        model=os.getenv("OPENCODE_GO_MODEL", DEFAULT_OPENCODE_GO_MODEL),
        api_key=_env_required("OPENCODE_GO_API_KEY"),
        temperature=temperature,
        timeout=timeout,
        api_style=os.getenv("OPENCODE_GO_API_STYLE", "auto"),
    )
