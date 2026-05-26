import os
from functools import lru_cache

import requests
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser

BASE_URL = "https://ceur-dev.wikidata.dbis.rwth-aachen.de"
TOKEN_URL = f"{BASE_URL}/token"
IMPORT_URL = f"{BASE_URL}/wd/import/"


def get_headers() -> dict[str, str]:
    if os.getenv("GITLAB_CI") != "true":
        load_dotenv()
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    if not username or not password:
        raise RuntimeError("The loading of login data failed!")

    try:
        response = requests.post(TOKEN_URL, data={"username": "KGL_Group_2@kglBot", "password": password})
        response.raise_for_status()
    except Exception as e:
        raise RuntimeError("The token request failed!") from e

    token = response.json().get("access_token")
    if not token:
        raise ValueError("The token was not present in the response!")

    return {"Authorization": f"Bearer {token}"}


@lru_cache(maxsize=1)
def get_llm():
    """
    Returns a LangChain Runnable that accepts a string prompt and returns a string.

    Configure via .env:
      LLM_PROVIDER      — ollama (default), openai, or anthropic
      LLM_MODEL         — model name (e.g. llama3.1:8b, gpt-4o-mini, claude-haiku-4-5-20251001)
      OLLAMA_BASE_URL   — Ollama server URL (default: http://localhost:11434)
      OPENAI_API_KEY    — required when LLM_PROVIDER=openai
      ANTHROPIC_API_KEY — required when LLM_PROVIDER=anthropic
    """
    if os.getenv("GITLAB_CI") != "true":
        load_dotenv()

    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    model_name = os.getenv("LLM_MODEL", "llama3.1:8b")

    if provider == "ollama":
        from langchain_ollama import OllamaLLM
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = OllamaLLM(model=model_name, base_url=base_url, temperature=0)
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        model = ChatOpenAI(model=model_name, temperature=0, api_key=api_key)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")
        model = ChatAnthropic(model=model_name, temperature=0, api_key=api_key)
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: '{provider}'. Choose from: ollama, openai, anthropic"
        )

    return model | StrOutputParser()
