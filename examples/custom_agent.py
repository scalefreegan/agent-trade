"""Example of creating a custom agent with the MCP tools."""

import os
from agent_trade.agent import create_agent

# Ensure API keys are set
os.environ["ANTHROPIC_API_KEY"] = "your_key_here"
os.environ["TIINGO_API_KEY"] = "your_key_here"  # optional
os.environ["NEWSAPI_KEY"] = "your_key_here"     # optional


def main():
    """Create a custom agent and run interactive queries."""

    # Create the agent
    agent = create_agent(model="claude-sonnet-4-5-20250929")

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
            response = agent.run(question)

            # Print the response
            print(f"\n{response.content}")
            print(f"\n(Tokens: {response.usage.input_tokens} in, {response.usage.output_tokens} out)")

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
