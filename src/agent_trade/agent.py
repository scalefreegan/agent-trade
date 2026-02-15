"""Anthropic API wrapper for headless queries with tool use."""

import os
import time
import json
from typing import Any
from anthropic import Anthropic
from . import stock_data, news_data
from .logging_config import log_tool_call


# Define tools as Anthropic function schemas
TOOLS = [
    {
        "name": "get_stock_info",
        "description": "Get current stock price and company information",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., 'AAPL', 'TSLA')"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_historical_prices",
        "description": "Get historical price data (OHLCV)",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol"
                },
                "period": {
                    "type": "string",
                    "description": "Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max",
                    "default": "1mo"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_dividend_history",
        "description": "Get dividend payment history",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol"
                },
                "period": {
                    "type": "string",
                    "description": "Time period: 1y, 2y, 5y, max",
                    "default": "5y"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_stock_splits",
        "description": "Get stock split history",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_stock_news",
        "description": "Get financial news for specific stock tickers (best for company-specific news)",
        "input_schema": {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of stock ticker symbols"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of articles",
                    "default": 10
                }
            },
            "required": ["tickers"]
        }
    },
    {
        "name": "search_news",
        "description": "Search general news by keyword (best for topics and trends)",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (keywords, phrases)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of articles",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    }
]

# Tool function mapping
TOOL_FUNCTIONS = {
    "get_stock_info": stock_data.get_stock_info,
    "get_historical_prices": stock_data.get_historical_prices,
    "get_dividend_history": stock_data.get_dividend_history,
    "get_stock_splits": stock_data.get_stock_splits,
    "get_stock_news": news_data.get_stock_news,
    "search_news": news_data.search_news,
}


def create_client() -> Anthropic:
    """Create Anthropic client.

    Returns:
        Configured Anthropic client instance
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable not set. "
            "Get your API key from https://console.anthropic.com/"
        )

    return Anthropic(api_key=api_key)


def query(question: str, model: str = "claude-sonnet-4-5-20250929", max_iterations: int = 5) -> dict[str, Any]:
    """Run a headless query using Anthropic API with tool use.

    Args:
        question: Question or query about stocks/news
        model: Claude model to use
        max_iterations: Maximum tool-use iterations

    Returns:
        Dictionary containing response and metadata
    """
    client = create_client()

    messages = [{"role": "user", "content": question}]
    total_input_tokens = 0
    total_output_tokens = 0

    for iteration in range(max_iterations):
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            tools=TOOLS,
            messages=messages
        )

        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        # Add assistant response to messages
        messages.append({"role": "assistant", "content": response.content})

        # Check if we're done (no tool use)
        if response.stop_reason != "tool_use":
            # Extract text response
            answer = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    answer += block.text

            return {
                "question": question,
                "answer": answer,
                "model": model,
                "iterations": iteration + 1,
                "usage": {
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                }
            }

        # Execute tools
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input

                # Execute the tool
                if tool_name in TOOL_FUNCTIONS:
                    start_time = time.time()
                    try:
                        result = TOOL_FUNCTIONS[tool_name](**tool_input)
                        execution_time_ms = (time.time() - start_time) * 1000

                        # Convert Pydantic model to JSON-serializable dict
                        # Use mode="json" to handle Decimal and other special types
                        result_dict = result.model_dump(mode="json") if hasattr(result, 'model_dump') else result

                        # Log successful tool call
                        log_tool_call(
                            tool_name=tool_name,
                            mode="api",
                            input_args=tool_input,
                            output=result_dict,
                            execution_time_ms=execution_time_ms,
                            model=model,
                        )

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result_dict)
                        })
                    except Exception as e:
                        execution_time_ms = (time.time() - start_time) * 1000

                        # Log failed tool call
                        log_tool_call(
                            tool_name=tool_name,
                            mode="api",
                            input_args=tool_input,
                            error=str(e),
                            execution_time_ms=execution_time_ms,
                            model=model,
                        )

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True
                        })

        # Add tool results to messages
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    # Max iterations reached
    return {
        "question": question,
        "answer": "Maximum iterations reached without completing the query",
        "model": model,
        "iterations": max_iterations,
        "usage": {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
        }
    }
