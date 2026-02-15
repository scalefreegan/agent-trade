"""Simple test script to verify MCP server functionality."""

import os
from agent_trade import stock_data, news_data

def test_stock_data():
    """Test stock data functions without API keys."""
    print("Testing stock data functions...")

    # Test get_stock_info
    try:
        result = stock_data.get_stock_info("AAPL")
        print(f"✓ get_stock_info: {result.symbol} - {result.name} - ${result.current_price}")
    except Exception as e:
        print(f"✗ get_stock_info failed: {e}")

    # Test get_historical_prices
    try:
        result = stock_data.get_historical_prices("AAPL", "5d")
        print(f"✓ get_historical_prices: Got {result.count} data points")
    except Exception as e:
        print(f"✗ get_historical_prices failed: {e}")

    # Test get_dividend_history
    try:
        result = stock_data.get_dividend_history("AAPL", "1y")
        print(f"✓ get_dividend_history: Got {result.count} dividend records")
    except Exception as e:
        print(f"✗ get_dividend_history failed: {e}")

    # Test get_stock_splits
    try:
        result = stock_data.get_stock_splits("AAPL")
        print(f"✓ get_stock_splits: Got {result.count} split records")
    except Exception as e:
        print(f"✗ get_stock_splits failed: {e}")

def test_news_data():
    """Test news data functions (requires API keys)."""
    print("\nTesting news data functions...")

    # Check for API keys
    tiingo_key = os.environ.get("TIINGO_API_KEY")
    newsapi_key = os.environ.get("NEWSAPI_KEY")

    if not tiingo_key:
        print("⚠ TIINGO_API_KEY not set - skipping Tiingo tests")
    else:
        try:
            result = news_data.get_stock_news(["AAPL"], limit=3)
            if result.error:
                print(f"✗ get_stock_news: {result.error}")
            else:
                print(f"✓ get_stock_news: Got {result.count} articles")
        except Exception as e:
            print(f"✗ get_stock_news failed: {e}")

    if not newsapi_key:
        print("⚠ NEWSAPI_KEY not set - skipping NewsAPI tests")
    else:
        try:
            result = news_data.search_news("Tesla", limit=3)
            if result.error:
                print(f"✗ search_news: {result.error}")
            else:
                print(f"✓ search_news: Got {result.count} articles")
        except Exception as e:
            print(f"✗ search_news failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Agent Trade MCP Server - Functionality Test")
    print("=" * 60)
    test_stock_data()
    test_news_data()
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
