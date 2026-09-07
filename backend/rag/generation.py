import os

from openai import OpenAI


CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen3.7-flash")
DASHSCOPE_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)


def generate_answer(messages: list[dict]) -> str:
    api_key = os.getenv("DASHSCOPE_API_KEY")

    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not set")

    client = OpenAI(api_key=api_key, base_url=DASHSCOPE_BASE_URL)

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.2,
    )

    answer = response.choices[0].message.content

    if not answer:
        raise RuntimeError("Generation model returned an empty answer")

    return answer.strip()
