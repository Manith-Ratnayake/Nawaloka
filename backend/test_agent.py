import asyncio

from dotenv import load_dotenv

from nawaloka_agent.agent import run_agent


load_dotenv()


async def main():
    question = input("Question: ").strip()
    model = input("Vercel AI Gateway model ID: ").strip()

    print()
    answer = await run_agent(question, model)
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())
