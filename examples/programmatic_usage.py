"""Example of programmatic usage with Claude Agent SDK."""

import os
from agent_trade import agent

# Ensure API keys are set
os.environ["ANTHROPIC_API_KEY"] = "your_key_here"
os.environ["TIINGO_API_KEY"] = "your_key_here"  # optional
os.environ["NEWSAPI_KEY"] = "your_key_here"     # optional


def main():
    """Run example queries programmatically."""

    queries = [
        "What is the current price of Apple stock?",
        "Get the historical prices for TSLA over the last month",
        "What dividends has Microsoft paid in the last year?",
        "Search for news about interest rate changes",
    ]

    for question in queries:
        print(f"\n{'='*60}")
        print(f"Q: {question}")
        print(f"{'='*60}")

        # Run the query
        result = agent.query(question)

        # Print the answer
        print(result["answer"])

        # Print token usage
        print(f"\nTokens: {result['usage']['input_tokens']} in, {result['usage']['output_tokens']} out")


if __name__ == "__main__":
    main()
