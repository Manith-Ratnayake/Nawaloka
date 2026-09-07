import os

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from openai import AsyncOpenAI

from nawaloka_agent.tools import search_website


AI_GATEWAY_BASE_URL = os.getenv(
    "AI_GATEWAY_BASE_URL",
    "https://ai-gateway.vercel.sh/v1",
)

set_tracing_disabled(True)


def create_model(model_id: str) -> OpenAIChatCompletionsModel:
    api_key = os.getenv("AI_GATEWAY_API_KEY")

    if not api_key:
        raise RuntimeError("AI_GATEWAY_API_KEY is not set")

    model_id = model_id.strip()

    if not model_id:
        raise ValueError("Model cannot be empty")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=AI_GATEWAY_BASE_URL,
    )

    return OpenAIChatCompletionsModel(
        model=model_id,
        openai_client=client,
    )


def create_agent(model_id: str) -> Agent:
    return Agent(
        name="Nawaloka Assistant",
        instructions="""You are the Nawaloka Hospitals assistant.

For Nawaloka-specific factual questions, always use the search_website tool before answering.
Use the retrieved website evidence as the source of truth.
Do not invent hospital information that is not supported by the tool result.
If the retrieved information is insufficient, clearly say that you could not find enough information in the indexed Nawaloka website content.
For simple greetings or conversational messages that do not require Nawaloka facts, you may answer without using a tool.
When useful, refer to retrieved evidence as Source 1, Source 2, and so on.
Keep answers clear and direct.""",
        model=create_model(model_id),
        tools=[search_website],
    )


async def run_agent(message: str, model_id: str) -> str:
    message = message.strip()

    if not message:
        raise ValueError("Message cannot be empty")

    print(f"[AGENT] Model: {model_id}")
    print(f"[AGENT] User: {message}")

    agent = create_agent(model_id)
    result = await Runner.run(agent, message, max_turns=6)

    if not result.final_output:
        raise RuntimeError("Agent returned an empty response")

    return str(result.final_output).strip()
