from functools import lru_cache

from openai import OpenAI

from . import config


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    # base_url=None means the normal OpenAI endpoint; set OPENAI_BASE_URL to use Gemini etc.
    return OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)
