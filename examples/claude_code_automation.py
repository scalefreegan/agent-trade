"""Examples of automating Claude Code CLI via run_agent."""

import asyncio
from agent_trade import claude_wrapper


async def example_simple_query():
    """Simple query through Claude Code."""
    print("=== Simple Query ===")

    result = await claude_wrapper.run_agent(
        'What is AAPL trading at right now? Return a JSON object with keys: symbol, price, currency.'
    )

    print(result)


async def example_query_with_system_prompt():
    """Query with a custom system prompt."""
    print("\n=== Query with System Prompt ===")

    result = await claude_wrapper.run_agent(
        prompt="Get historical prices for TSLA over 1 month and summarize the trend.",
        system_prompt="Return your answer as a JSON object with keys: summary, trend, data.",
        max_turns=10,
    )

    print(result)


async def main():
    """Run all examples."""
    await example_simple_query()
    await example_query_with_system_prompt()


if __name__ == "__main__":
    print("Claude Code Automation Examples")
    print("=" * 60)
    print("Note: Requires agent-trade MCP server configured in Claude Code")
    print("=" * 60)

    asyncio.run(main())
