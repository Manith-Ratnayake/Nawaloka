from rag.pipeline import run_rag


if __name__ == "__main__":
    question = input("Question: ").strip()
    print()
    print(run_rag(question))
