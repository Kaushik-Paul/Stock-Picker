import os

from crewai import LLM
from dotenv import load_dotenv

load_dotenv()


def _env_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def create_llm(
    *,
    temperature: float | None = 0.7,
    timeout: float | int | None = None,
) -> LLM:
    base_url = _env_required("BASE_URL")
    api_key = _env_required("API_KEY")
    model = _env_required("MODEL").removeprefix("openai/")

    return LLM(
        model=f"openai/{model}",
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        timeout=timeout,
    )
