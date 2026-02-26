"""Tests for portfolio_tracker.py."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from agent_trade.experiment.models import Portfolio, StockPosition, TaxLot
from agent_trade.experiment.portfolio_tracker import (
    add_shares,
    calculate_portfolio_metrics,
    remove_shares_fifo,
    validate_position_limit,
)


class TestAddShares:
    """Tests for add_shares function."""

    def test_add_shares_to_empty_portfolio(self):
        """Test adding shares to a portfolio with no existing position."""
        portfolio = Portfolio(cash=Decimal("1000"))
        now = datetime.now(timezone.utc)

        add_shares(
            portfolio=portfolio,
            symbol="AAPL",
            shares=Decimal("10"),
            cost_basis=Decimal("100"),
            purchase_date=now,
        )

        assert len(portfolio.positions) == 1
        position = portfolio.positions[0]
        assert position.symbol == "AAPL"
        assert position.total_shares == Decimal("10")
        assert len(position.lots) == 1
        assert position.lots[0].shares == Decimal("10")
        assert position.lots[0].cost_basis == Decimal("100")
        assert position.lots[0].purchase_date == now

    def test_add_shares_to_existing_position(self):
        """Test adding shares to an existing position creates new lot."""
        now = datetime.now(timezone.utc)
        later = now + timedelta(days=30)

        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("1000"), positions=[position])

        add_shares(
            portfolio=portfolio,
            symbol="AAPL",
            shares=Decimal("5"),
            cost_basis=Decimal("110"),
            purchase_date=later,
        )

        assert len(portfolio.positions) == 1
        assert portfolio.positions[0].total_shares == Decimal("15")
        assert len(portfolio.positions[0].lots) == 2
        assert portfolio.positions[0].lots[1].shares == Decimal("5")
        assert portfolio.positions[0].lots[1].cost_basis == Decimal("110")

    def test_add_shares_negative_raises_error(self):
        """Test that adding negative shares raises ValueError."""
        portfolio = Portfolio(cash=Decimal("1000"))
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="Cannot add non-positive shares"):
            add_shares(
                portfolio=portfolio,
                symbol="AAPL",
                shares=Decimal("-5"),
                cost_basis=Decimal("100"),
                purchase_date=now,
            )

    def test_add_shares_zero_cost_basis_raises_error(self):
        """Test that zero cost basis raises ValueError."""
        portfolio = Portfolio(cash=Decimal("1000"))
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="Cannot add shares with non-positive cost basis"):
            add_shares(
                portfolio=portfolio,
                symbol="AAPL",
                shares=Decimal("10"),
                cost_basis=Decimal("0"),
                purchase_date=now,
            )


class TestRemoveSharesFifo:
    """Tests for remove_shares_fifo function."""

    def test_remove_shares_from_single_lot_partial(self):
        """Test partial sale from a single lot."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])

        lot_sales = remove_shares_fifo(
            portfolio=portfolio,
            symbol="AAPL",
            shares_to_sell=Decimal("6"),
            as_of=now + timedelta(days=100),
        )

        assert len(lot_sales) == 1
        lot, shares_sold = lot_sales[0]
        assert shares_sold == Decimal("6")
        assert lot.cost_basis == Decimal("100")

        # Position should still exist with 4 shares
        position = portfolio.get_position("AAPL")
        assert position is not None
        assert position.total_shares == Decimal("4")
        assert len(position.lots) == 1

    def test_remove_shares_from_single_lot_full(self):
        """Test full sale of a single lot removes position."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])

        lot_sales = remove_shares_fifo(
            portfolio=portfolio,
            symbol="AAPL",
            shares_to_sell=Decimal("10"),
            as_of=now + timedelta(days=100),
        )

        assert len(lot_sales) == 1
        lot, shares_sold = lot_sales[0]
        assert shares_sold == Decimal("10")

        # Position should be removed
        assert portfolio.get_position("AAPL") is None
        assert len(portfolio.positions) == 0

    def test_remove_shares_fifo_multiple_lots(self):
        """Test FIFO removes from oldest lots first."""
        now = datetime.now(timezone.utc)
        later1 = now + timedelta(days=30)
        later2 = now + timedelta(days=60)

        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now),
                TaxLot(shares=Decimal("8"), cost_basis=Decimal("110"), purchase_date=later1),
                TaxLot(shares=Decimal("5"), cost_basis=Decimal("120"), purchase_date=later2),
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])

        # Sell 15 shares (should take all of lot 1 and 5 from lot 2)
        lot_sales = remove_shares_fifo(
            portfolio=portfolio,
            symbol="AAPL",
            shares_to_sell=Decimal("15"),
            as_of=later2 + timedelta(days=10),
        )

        assert len(lot_sales) == 2
        # First lot: fully sold
        assert lot_sales[0][1] == Decimal("10")
        assert lot_sales[0][0].cost_basis == Decimal("100")
        # Second lot: partially sold
        assert lot_sales[1][1] == Decimal("5")
        assert lot_sales[1][0].cost_basis == Decimal("110")

        # Position should have 8 shares remaining (3 from lot 2, 5 from lot 3)
        position = portfolio.get_position("AAPL")
        assert position.total_shares == Decimal("8")
        assert len(position.lots) == 2
        assert position.lots[0].shares == Decimal("3")  # Remaining from lot 2
        assert position.lots[1].shares == Decimal("5")  # Untouched lot 3

    def test_remove_shares_insufficient_shares_raises_error(self):
        """Test that insufficient shares raises ValueError."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])

        with pytest.raises(ValueError, match="Insufficient shares"):
            remove_shares_fifo(
                portfolio=portfolio,
                symbol="AAPL",
                shares_to_sell=Decimal("15"),
                as_of=now + timedelta(days=10),
            )

    def test_remove_shares_from_nonexistent_position_raises_error(self):
        """Test removing shares from nonexistent position raises ValueError."""
        portfolio = Portfolio(cash=Decimal("500"))

        with pytest.raises(ValueError, match="Insufficient shares"):
            remove_shares_fifo(
                portfolio=portfolio,
                symbol="AAPL",
                shares_to_sell=Decimal("10"),
                as_of=datetime.now(timezone.utc),
            )

    def test_remove_shares_negative_raises_error(self):
        """Test that negative shares raises ValueError."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])

        with pytest.raises(ValueError, match="Cannot sell non-positive shares"):
            remove_shares_fifo(
                portfolio=portfolio,
                symbol="AAPL",
                shares_to_sell=Decimal("-5"),
                as_of=now + timedelta(days=10),
            )

    def test_remove_shares_negligible_remainder_removes_lot(self):
        """Test that selling shares leaving negligible remainder (<0.0001) removes the lot."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("10.0000"), cost_basis=Decimal("100"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])

        # Sell 9.9999 shares, leaving 0.0001 shares (should remove the lot and position)
        lot_sales = remove_shares_fifo(
            portfolio=portfolio,
            symbol="AAPL",
            shares_to_sell=Decimal("9.9999"),
            as_of=now + timedelta(days=100),
        )

        assert len(lot_sales) == 1
        assert lot_sales[0][1] == Decimal("9.9999")

        # Position should be removed because remaining shares are < 0.0001
        assert portfolio.get_position("AAPL") is None
        assert len(portfolio.positions) == 0


class TestValidatePositionLimit:
    """Tests for validate_position_limit function."""

    def test_validate_position_limit_small_buy_exceeds_limit(self):
        """Test that even a small buy can exceed position limit."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("5"), cost_basis=Decimal("100"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])
        current_prices = {"AAPL": Decimal("100")}

        # Buying $200 more of AAPL: total would be $700 out of $1200 = 58% > 50% limit
        # But let's test a passing case: buying $100 more
        valid, error = validate_position_limit(
            portfolio=portfolio,
            symbol="AAPL",
            additional_shares=Decimal("1"),
            share_price=Decimal("100"),
            current_prices=current_prices,
            max_position_pct=Decimal("0.50"),
        )

        # Total portfolio after buy: $500 cash + $500 AAPL + $100 buy = $1100
        # AAPL position after buy: $500 + $100 = $600 = 54.5% > 50%, should fail
        assert not valid
        assert "Position limit exceeded" in error

    def test_validate_position_limit_exceeds_limit(self):
        """Test that position exceeding limit fails validation."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("5"), cost_basis=Decimal("100"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])
        current_prices = {"AAPL": Decimal("100")}

        # Try to buy $600 more of AAPL
        valid, error = validate_position_limit(
            portfolio=portfolio,
            symbol="AAPL",
            additional_shares=Decimal("6"),
            share_price=Decimal("100"),
            current_prices=current_prices,
            max_position_pct=Decimal("0.50"),
        )

        assert not valid
        assert "Position limit exceeded" in error

    def test_validate_position_limit_new_position(self):
        """Test position limit for a new position."""
        portfolio = Portfolio(cash=Decimal("1000"))
        current_prices: dict[str, Decimal] = {}

        # Buying $400 of AAPL when total is $1400 = 28.6%, should pass
        valid, error = validate_position_limit(
            portfolio=portfolio,
            symbol="AAPL",
            additional_shares=Decimal("4"),
            share_price=Decimal("100"),
            current_prices=current_prices,
            max_position_pct=Decimal("0.50"),
        )

        assert valid
        assert error is None


class TestCalculatePortfolioMetrics:
    """Tests for calculate_portfolio_metrics function."""

    def test_calculate_metrics_cash_only(self):
        """Test metrics calculation for cash-only portfolio."""
        portfolio = Portfolio(cash=Decimal("1000"))
        current_prices: dict[str, Decimal] = {}

        metrics = calculate_portfolio_metrics(portfolio, current_prices)

        assert metrics["total_value"] == Decimal("1000")
        assert metrics["cash"] == Decimal("1000")
        assert metrics["stock_value"] == Decimal("0")
        assert metrics["total_cost"] == Decimal("0")
        assert metrics["unrealized_gain_loss"] == Decimal("0")
        assert metrics["cash_pct"] == Decimal("100")

    def test_calculate_metrics_with_positions(self):
        """Test metrics calculation with stock positions."""
        now = datetime.now(timezone.utc)
        positions = [
            StockPosition(
                symbol="AAPL",
                lots=[
                    TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)
                ],
            ),
            StockPosition(
                symbol="GOOGL",
                lots=[
                    TaxLot(shares=Decimal("5"), cost_basis=Decimal("200"), purchase_date=now)
                ],
            ),
        ]
        portfolio = Portfolio(cash=Decimal("500"), positions=positions)
        current_prices = {"AAPL": Decimal("110"), "GOOGL": Decimal("210")}

        metrics = calculate_portfolio_metrics(portfolio, current_prices)

        # AAPL: 10 shares * $110 = $1100 (cost: $1000, gain: $100)
        # GOOGL: 5 shares * $210 = $1050 (cost: $1000, gain: $50)
        # Total value: $500 + $1100 + $1050 = $2650
        assert metrics["total_value"] == Decimal("2650")
        assert metrics["cash"] == Decimal("500")
        assert metrics["stock_value"] == Decimal("2150")
        assert metrics["total_cost"] == Decimal("2000")
        assert metrics["unrealized_gain_loss"] == Decimal("150")
        assert abs(metrics["cash_pct"] - Decimal("18.87")) < Decimal("0.01")

    def test_calculate_metrics_with_losses(self):
        """Test metrics calculation with unrealized losses."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])
        current_prices = {"AAPL": Decimal("80")}  # Down from $100

        metrics = calculate_portfolio_metrics(portfolio, current_prices)

        assert metrics["total_value"] == Decimal("1300")
        assert metrics["stock_value"] == Decimal("800")
        assert metrics["total_cost"] == Decimal("1000")
        assert metrics["unrealized_gain_loss"] == Decimal("-200")

    def test_calculate_metrics_missing_price_raises_error(self):
        """Test that missing price raises KeyError."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])
        current_prices: dict[str, Decimal] = {}  # Missing AAPL price

        with pytest.raises(KeyError, match="Missing market price for held symbol AAPL"):
            calculate_portfolio_metrics(portfolio, current_prices)
