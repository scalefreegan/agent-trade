"""Examples of automating Claude Code CLI."""

import asyncio
from agent_trade import claude_wrapper


async def example_simple_query():
    """Simple query through Claude Code."""
    print("=== Simple Query ===")

    result = await claude_wrapper.get_stock_data_via_claude(
        "What is AAPL trading at?"
    )

    print(result)


async def example_streaming_query():
    """Stream messages from Claude Code."""
    print("\n=== Streaming Query ===")

    async for message in claude_wrapper.query_claude_code(
        "Get historical prices for TSLA over 1 month"
    ):
        print(f"Message: {message}")


async def example_run_skill():
    """Run a Claude Code skill."""
    print("\n=== Run Skill ===")

    async for message in claude_wrapper.run_skill(
        "commit",
        args="-m 'Update documentation'"
    ):
        print(f"Skill message: {message}")


async def example_interactive_session():
    """Interactive session with Claude Code."""
    print("\n=== Interactive Session ===")

    async with claude_wrapper.ClaudeCodeSession() as session:
        # First query
        response1 = await session.query("What is AAPL trading at?")
        print(f"Response 1: {response1}")

        # Follow-up query (with context)
        response2 = await session.query("Now get news about Apple")
        print(f"Response 2: {response2}")

        # Check conversation history
        print(f"\nConversation history: {len(session.conversation_history)} messages")


async def example_workflow():
    """Complex workflow using Claude Code automation."""
    print("\n=== Workflow Example ===")

    async with claude_wrapper.ClaudeCodeSession(
        permission_mode="acceptEdits"  # Auto-accept file edits
    ) as session:
        # Step 1: Get stock data
        stock_data = await session.query("Get current info for AAPL")
        print(f"Stock data: {stock_data[:200]}...")

        # Step 2: Analyze with AI (Claude Code can use all tools)
        analysis = await session.query(
            "Based on that data, should I buy, sell, or hold?"
        )
        print(f"Analysis: {analysis}")

        # Step 3: Get news
        news = await session.query("Get news about Apple stock")
        print(f"News: {news[:200]}...")


async def main():
    """Run all examples."""
    # Simple query
    await example_simple_query()

    # Streaming (commented out - verbose)
    # await example_streaming_query()

    # Run skill (commented out - would actually commit)
    # await example_run_skill()

    # Interactive session
    await example_interactive_session()

    # Workflow
    await example_workflow()


if __name__ == "__main__":
    print("Claude Code Automation Examples")
    print("=" * 60)
    print("Note: Requires agent-trade MCP server configured in Claude Code")
    print("=" * 60)

    asyncio.run(main())
