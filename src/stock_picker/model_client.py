import os
import json
from inspect import signature
from typing import Any, Dict, List, Optional, Union

from crewai import LLM
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


def using_opencode_go() -> bool:
    return not _env_bool("USE_OPENROUTER", default=False)


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


def opencode_go_model_id() -> str:
    return _opencode_go_model(os.getenv("OPENCODE_GO_MODEL", DEFAULT_OPENCODE_GO_MODEL))


def opencode_go_uses_anthropic_endpoint(model: Optional[str] = None) -> bool:
    model = _opencode_go_model(model or opencode_go_model_id())
    return model.startswith("minimax-")


def opencode_go_tools_enabled() -> bool:
    override = os.getenv("OPENCODE_GO_ENABLE_TOOLS")
    if override is not None:
        return _env_bool("OPENCODE_GO_ENABLE_TOOLS")
    return not opencode_go_uses_anthropic_endpoint()


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if "text" in item:
                    parts.append(str(item["text"]))
                elif "content" in item:
                    parts.append(_content_to_text(item["content"]))
                elif item.get("type") in {"tool_use", "tool_result"}:
                    continue
                else:
                    parts.append(json.dumps(item))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    if isinstance(content, dict):
        if "text" in content:
            return str(content["text"])
        if "content" in content:
            return _content_to_text(content["content"])
        return json.dumps(content)
    return str(content)


class OpenCodeGoAutoLLM(LLM):
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
        if opencode_go_uses_anthropic_endpoint(self._model_id):
            return "anthropic"
        return "openai"

    def _client_for(self, protocol: str) -> LLM:
        return self._anthropic_llm if protocol == "anthropic" else self._openai_llm

    def _alternate_protocol(self) -> str:
        return "anthropic" if self._active_protocol == "openai" else "openai"

    @staticmethod
    def _call_llm(
        llm: LLM,
        *,
        messages: Union[str, List[Dict[str, str]]],
        tools: Optional[List[dict]],
        callbacks: Optional[List[Any]],
        available_functions: Optional[Dict[str, Any]],
        from_task: Optional[Any],
        from_agent: Optional[Any],
    ) -> Union[str, Any]:
        call_kwargs = {
            "messages": messages,
            "tools": tools,
            "callbacks": callbacks,
            "available_functions": available_functions,
            "from_task": from_task,
            "from_agent": from_agent,
        }
        accepted_params = signature(llm.call).parameters
        supported_kwargs = {
            name: value
            for name, value in call_kwargs.items()
            if name in accepted_params and (name == "messages" or value is not None)
        }
        return _content_to_text(llm.call(**supported_kwargs))

    def call(
        self,
        messages: Union[str, List[Dict[str, str]]],
        tools: Optional[List[dict]] = None,
        callbacks: Optional[List[Any]] = None,
        available_functions: Optional[Dict[str, Any]] = None,
        from_task: Optional[Any] = None,
        from_agent: Optional[Any] = None,
    ) -> Union[str, Any]:
        try:
            result = self._call_llm(
                self._client_for(self._active_protocol),
                messages=messages,
                tools=tools,
                callbacks=callbacks,
                available_functions=available_functions,
                from_task=from_task,
                from_agent=from_agent,
            )
            self._protocol_cache[self._model_id] = self._active_protocol
            return result
        except Exception as first_error:
            if self._api_style != "auto":
                raise
            first_protocol = self._active_protocol
            self._active_protocol = self._alternate_protocol()
            try:
                result = self._call_llm(
                    self._client_for(self._active_protocol),
                    messages=messages,
                    tools=tools,
                    callbacks=callbacks,
                    available_functions=available_functions,
                    from_task=from_task,
                    from_agent=from_agent,
                )
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
) -> LLM:
    if not using_opencode_go():
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
        model=opencode_go_model_id(),
        api_key=_env_required("OPENCODE_GO_API_KEY"),
        temperature=temperature,
        timeout=timeout,
        api_style=os.getenv("OPENCODE_GO_API_STYLE", "auto"),
    )
