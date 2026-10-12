from functools import lru_cache

from openai import OpenAI

from . import config


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    return OpenAI(api_key=config.OPENAI_API_KEY)
