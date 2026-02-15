"""Example of creating a custom interactive agent using the query API."""

import os
from agent_trade import agent

# Ensure API keys are set
os.environ["ANTHROPIC_API_KEY"] = "your_key_here"
os.environ["TIINGO_API_KEY"] = "your_key_here"  # optional
os.environ["NEWSAPI_KEY"] = "your_key_here"     # optional


def main():
    """Run interactive queries using the agent API."""

    print("Stock Market Agent - Interactive Mode")
    print("Type 'quit' to exit\n")

    while True:
        # Get user input
        question = input("\nYour question: ").strip()

        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        if not question:
            continue

        try:
            # Run the query
            result = agent.query(question)

            # Print the response
            print(f"\n{result['answer']}")
            print(f"\n(Tokens: {result['usage']['input_tokens']} in, {result['usage']['output_tokens']} out)")

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
