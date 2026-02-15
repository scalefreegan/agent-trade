"""Example of orchestration workflows for stock market analysis."""

import os
from agent_trade.orchestration import Workflow, Pipeline, ExecutionMode
from agent_trade import stock_data, agent

# Setup (ensure API keys are set)
os.environ["ANTHROPIC_API_KEY"] = "your_key_here"


def example_sequential_workflow():
    """Example: Sequential workflow for stock analysis."""

    workflow = Workflow("stock_analysis", mode=ExecutionMode.SEQUENTIAL)

    # Step 1: Get current stock info
    workflow.add_step(
        "get_info",
        stock_data.get_stock_info,
        "AAPL"
    )

    # Step 2: Get historical prices
    workflow.add_step(
        "get_history",
        stock_data.get_historical_prices,
        "AAPL",
        period="1mo"
    )

    # Step 3: Get dividend history
    workflow.add_step(
        "get_dividends",
        stock_data.get_dividend_history,
        "AAPL",
        period="1y"
    )

    # Execute
    result = workflow.execute()

    print(f"Executed steps: {result.steps_executed}")
    print(f"Success: {result.success}")

    if result.success:
        info = result.results["get_info"]
        print(f"\nCurrent price: ${info['current_price']}")
        print(f"52-week high: ${info['52_week_high']}")


def example_parallel_workflow():
    """Example: Parallel workflow for multiple stocks."""

    workflow = Workflow("multi_stock_check", mode=ExecutionMode.PARALLEL)

    # Get info for multiple stocks in parallel
    for symbol in ["AAPL", "GOOGL", "MSFT", "TSLA"]:
        workflow.add_step(
            f"get_{symbol}",
            stock_data.get_stock_info,
            symbol
        )

    # Execute
    result = workflow.execute()

    print(f"Stocks analyzed: {len(result.results)}")

    for step_name, data in result.results.items():
        symbol = data['symbol']
        price = data['current_price']
        print(f"{symbol}: ${price}")


def example_conditional_workflow():
    """Example: Conditional workflow based on stock price."""

    def should_analyze(context: dict) -> bool:
        """Check if stock price is above threshold."""
        info = context.get("get_info", {})
        price = info.get("current_price", 0)
        return price > 200  # Only analyze if price > $200

    workflow = Workflow("conditional_analysis", mode=ExecutionMode.CONDITIONAL)

    # Always get stock info
    workflow.add_step(
        "get_info",
        stock_data.get_stock_info,
        "AAPL",
        condition=lambda ctx: True  # Always execute
    )

    # Only get history if price > $200
    workflow.add_step(
        "get_history",
        stock_data.get_historical_prices,
        "AAPL",
        period="3mo",
        condition=should_analyze
    )

    # Execute
    result = workflow.execute()

    print(f"Steps executed: {result.steps_executed}")
    print(f"Price threshold triggered: {'get_history' in result.steps_executed}")


def example_agent_workflow():
    """Example: Workflow combining data retrieval and AI analysis."""

    workflow = Workflow("ai_stock_analysis", mode=ExecutionMode.SEQUENTIAL)

    # Step 1: Get stock data
    workflow.add_step(
        "get_data",
        stock_data.get_stock_info,
        "TSLA"
    )

    # Step 2: Analyze with Claude
    def analyze_stock(context: dict):
        """Use Claude to analyze the stock data."""
        data = context["get_data"]
        question = f"""
        Analyze this stock data and provide investment insights:

        Symbol: {data['symbol']}
        Price: ${data['current_price']}
        PE Ratio: {data['pe_ratio']}
        52-week high: ${data['52_week_high']}
        52-week low: ${data['52_week_low']}

        Is this a good time to buy, sell, or hold?
        """
        return agent.query(question)

    workflow.add_step(
        "ai_analysis",
        analyze_stock,
        # Pass context as kwargs
    )

    # Execute
    result = workflow.execute()

    if result.success:
        print("Stock Data:")
        print(result.results["get_data"])
        print("\nAI Analysis:")
        print(result.results["ai_analysis"]["answer"])


def example_pipeline():
    """Example: Pipeline combining multiple workflows."""

    pipeline = Pipeline("complete_stock_analysis")

    # Workflow 1: Data collection
    data_workflow = Workflow("data_collection", ExecutionMode.PARALLEL)
    for symbol in ["AAPL", "TSLA"]:
        data_workflow.add_step(
            f"info_{symbol}",
            stock_data.get_stock_info,
            symbol
        )

    # Workflow 2: Analysis
    analysis_workflow = Workflow("analysis", ExecutionMode.SEQUENTIAL)
    # Add analysis steps...

    # Add workflows to pipeline
    pipeline.add_workflow(data_workflow)
    pipeline.add_workflow(analysis_workflow)

    # Execute entire pipeline
    results = pipeline.execute()

    for workflow_name, result in results.items():
        print(f"\n{workflow_name}: {result.success}")
        print(f"  Steps: {result.steps_executed}")


if __name__ == "__main__":
    print("=== Sequential Workflow ===")
    example_sequential_workflow()

    print("\n=== Parallel Workflow ===")
    example_parallel_workflow()

    print("\n=== Conditional Workflow ===")
    example_conditional_workflow()

    # Uncomment to test AI workflows (requires ANTHROPIC_API_KEY)
    # print("\n=== Agent Workflow ===")
    # example_agent_workflow()

    # print("\n=== Pipeline ===")
    # example_pipeline()
