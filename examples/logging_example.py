"""Example of using tool logging."""

from agent_trade import agent
from agent_trade.logging_config import get_usage_stats, get_logger


def example_with_logging():
    """Run queries and view logs."""
    import os

    # Set API key
    os.environ["ANTHROPIC_API_KEY"] = "your_key_here"

    print("=== Running Queries ===\n")

    # Run some queries (will be automatically logged)
    result1 = agent.query("What is AAPL trading at?")
    print(f"Query 1: {result1['answer'][:100]}...")

    result2 = agent.query("Get historical prices for TSLA")
    print(f"Query 2: {result2['answer'][:100]}...")

    # Get usage statistics
    print("\n=== Usage Statistics ===\n")
    stats = get_usage_stats()

    print(f"Total calls: {stats['total_calls']}")
    print(f"Errors: {stats['errors']}")
    print(f"Total execution time: {stats['total_execution_time_ms']:.2f} ms")

    print("\nBy tool:")
    for tool, count in stats['by_tool'].items():
        print(f"  {tool}: {count}")

    print("\nBy mode:")
    for mode, count in stats['by_mode'].items():
        print(f"  {mode}: {count}")

    # Get logger instance for custom logging
    logger = get_logger()
    print(f"\nLog file location: {logger.log_file}")


def example_custom_logging():
    """Example of custom logging configuration."""
    from pathlib import Path
    from agent_trade.logging_config import ToolLogger, LogLevel

    # Create custom logger
    logger = ToolLogger(
        log_file=Path("./custom_logs.jsonl"),
        log_level=LogLevel.DEBUG,
        console_output=True,
    )

    # Log custom events
    logger.log_tool_call(
        tool_name="custom_tool",
        mode="custom",
        input_args={"param": "value"},
        output={"result": "success"},
        execution_time_ms=123.45,
    )

    # Get stats
    stats = logger.get_stats()
    print(f"Custom logger stats: {stats}")


def example_env_configuration():
    """Example of configuring logging via environment variables."""
    import os
    from agent_trade.logging_config import get_logger

    # Configure via env vars
    os.environ["AGENT_TRADE_LOG_FILE"] = "/tmp/agent-trade.jsonl"
    os.environ["AGENT_TRADE_LOG_LEVEL"] = "DEBUG"
    os.environ["AGENT_TRADE_LOG_CONSOLE"] = "true"

    # Get logger (will use env vars)
    logger = get_logger()

    print(f"Log file: {logger.log_file}")
    print(f"Log level: {logger.log_level}")


if __name__ == "__main__":
    print("Tool Logging Examples")
    print("=" * 60)

    # Run examples
    # example_with_logging()
    # example_custom_logging()
    example_env_configuration()
