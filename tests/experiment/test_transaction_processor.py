"""Tests for transaction_processor.py."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from agent_trade.experiment.models import (
    ExperimentConfig,
    Order,
    Portfolio,
    StockPosition,
    TaxLot,
)
from agent_trade.experiment.transaction_processor import (
    execute_buy,
    execute_order,
    execute_sell,
)


@pytest.fixture
def config():
    """Create a test experiment config."""
    return ExperimentConfig(
        experiment_id="test_exp",
        name="Test Experiment",
        num_agents=5,
        starting_capital=Decimal("1000"),
        short_term_tax_rate=Decimal("0.35"),
        long_term_tax_rate=Decimal("0.15"),
        long_term_holding_days=365,
        max_position_pct=Decimal("0.50"),
        min_trade_amount=Decimal("1.00"),
        created_at=datetime.now(timezone.utc),
        status="active",
    )


class TestExecuteBuy:
    """Tests for execute_buy function."""

    def test_execute_buy_creates_new_position(self, config):
        """Test buying creates new position with tax lot."""
        portfolio = Portfolio(cash=Decimal("1000"))
        order = Order(
            action="buy",
            symbol="AAPL",
            amount=Decimal("500"),  # Dollar amount
            reasoning="Good value",
        )
        now = datetime.now(timezone.utc)

        transaction = execute_buy(
            portfolio=portfolio,
            order=order,
            current_price=Decimal("100"),
            agent_id="agent_001",
            config=config,
            timestamp=now,
        )

        # Verify transaction details
        assert transaction.action == "buy"
        assert transaction.symbol == "AAPL"
        assert transaction.shares == Decimal("5")  # $500 / $100 = 5 shares
        assert transaction.price_per_share == Decimal("100")
        assert transaction.gross_amount == Decimal("500")
        assert transaction.tax_amount == Decimal("0")
        assert transaction.net_amount == Decimal("-500")
        assert transaction.lot_sales is None

        # Verify portfolio changes
        assert portfolio.cash == Decimal("500")
        assert len(portfolio.positions) == 1
        position = portfolio.positions[0]
        assert position.symbol == "AAPL"
        assert position.total_shares == Decimal("5")
        assert len(position.lots) == 1
        assert position.lots[0].cost_basis == Decimal("100")

    def test_execute_buy_adds_to_existing_position(self, config):
        """Test buying adds new lot to existing position."""
        now = datetime.now(timezone.utc)
        existing_position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("5"), cost_basis=Decimal("90"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("1000"), positions=[existing_position])

        order = Order(
            action="buy", symbol="AAPL", amount=Decimal("300"), reasoning="Add to position"
        )

        transaction = execute_buy(
            portfolio=portfolio,
            order=order,
            current_price=Decimal("100"),
            agent_id="agent_001",
            config=config,
            timestamp=now + timedelta(days=30),
        )

        assert transaction.shares == Decimal("3")
        assert portfolio.cash == Decimal("700")

        position = portfolio.get_position("AAPL")
        assert position.total_shares == Decimal("8")
        assert len(position.lots) == 2
        assert position.lots[1].shares == Decimal("3")
        assert position.lots[1].cost_basis == Decimal("100")

    def test_execute_buy_insufficient_cash_raises_error(self, config):
        """Test buying with insufficient cash raises ValueError."""
        portfolio = Portfolio(cash=Decimal("100"))
        order = Order(
            action="buy", symbol="AAPL", amount=Decimal("500"), reasoning="Too much"
        )

        with pytest.raises(ValueError, match="Insufficient cash"):
            execute_buy(
                portfolio=portfolio,
                order=order,
                current_price=Decimal("100"),
                agent_id="agent_001",
                config=config,
            )

    def test_execute_buy_below_minimum_raises_error(self, config):
        """Test buying below minimum trade amount raises ValueError."""
        portfolio = Portfolio(cash=Decimal("1000"))
        order = Order(
            action="buy", symbol="AAPL", amount=Decimal("0.50"), reasoning="Too small"
        )

        with pytest.raises(ValueError, match="Buy order validation failed"):
            execute_buy(
                portfolio=portfolio,
                order=order,
                current_price=Decimal("100"),
                agent_id="agent_001",
                config=config,
            )

    def test_execute_buy_invalid_price_raises_error(self, config):
        """Test buying with invalid price raises ValueError."""
        portfolio = Portfolio(cash=Decimal("1000"))
        order = Order(action="buy", symbol="AAPL", amount=Decimal("100"), reasoning="Bad price")

        with pytest.raises(ValueError, match="Invalid market price"):
            execute_buy(
                portfolio=portfolio,
                order=order,
                current_price=Decimal("0"),
                agent_id="agent_001",
                config=config,
            )


class TestExecuteSell:
    """Tests for execute_sell function."""

    def test_execute_sell_short_term_gain(self, config):
        """Test selling with short-term capital gain applies 35% tax."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])

        order = Order(action="sell", symbol="AAPL", amount=Decimal("10"), reasoning="Take profit")

        # Sell 100 days later (short-term)
        transaction = execute_sell(
            portfolio=portfolio,
            order=order,
            current_price=Decimal("120"),
            agent_id="agent_001",
            config=config,
            timestamp=now + timedelta(days=100),
        )

        # Capital gain: 10 shares * ($120 - $100) = $200
        # Tax: $200 * 0.35 = $70
        # Net proceeds: $1200 - $70 = $1130
        assert transaction.shares == Decimal("10")
        assert transaction.gross_amount == Decimal("1200")
        assert transaction.tax_amount == Decimal("70")
        assert transaction.net_amount == Decimal("1130")

        assert len(transaction.lot_sales) == 1
        lot_sale = transaction.lot_sales[0]
        assert lot_sale.holding_period_days == 100
        assert not lot_sale.is_long_term
        assert lot_sale.capital_gain == Decimal("200")
        assert lot_sale.tax_rate == Decimal("0.35")
        assert lot_sale.tax_amount == Decimal("70")

        # Portfolio should have cash + proceeds
        assert portfolio.cash == Decimal("1630")
        assert len(portfolio.positions) == 0

    def test_execute_sell_long_term_gain(self, config):
        """Test selling with long-term capital gain applies 15% tax."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])

        order = Order(action="sell", symbol="AAPL", amount=Decimal("10"), reasoning="Long hold")

        # Sell 400 days later (long-term)
        transaction = execute_sell(
            portfolio=portfolio,
            order=order,
            current_price=Decimal("120"),
            agent_id="agent_001",
            config=config,
            timestamp=now + timedelta(days=400),
        )

        # Capital gain: 10 shares * ($120 - $100) = $200
        # Tax: $200 * 0.15 = $30
        # Net proceeds: $1200 - $30 = $1170
        assert transaction.tax_amount == Decimal("30")
        assert transaction.net_amount == Decimal("1170")

        lot_sale = transaction.lot_sales[0]
        assert lot_sale.holding_period_days == 400
        assert lot_sale.is_long_term
        assert lot_sale.tax_rate == Decimal("0.15")
        assert lot_sale.tax_amount == Decimal("30")

        assert portfolio.cash == Decimal("1670")

    def test_execute_sell_capital_loss_no_tax(self, config):
        """Test selling at a loss has no tax."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])

        order = Order(action="sell", symbol="AAPL", amount=Decimal("10"), reasoning="Cut loss")

        transaction = execute_sell(
            portfolio=portfolio,
            order=order,
            current_price=Decimal("80"),
            agent_id="agent_001",
            config=config,
            timestamp=now + timedelta(days=100),
        )

        # Capital loss: 10 shares * ($80 - $100) = -$200
        # No tax on losses
        assert transaction.gross_amount == Decimal("800")
        assert transaction.tax_amount == Decimal("0")
        assert transaction.net_amount == Decimal("800")

        lot_sale = transaction.lot_sales[0]
        assert lot_sale.capital_gain == Decimal("-200")
        assert lot_sale.tax_amount == Decimal("0")

        assert portfolio.cash == Decimal("1300")

    def test_execute_sell_fifo_multiple_lots(self, config):
        """Test selling uses FIFO and calculates per-lot taxes."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[
                # Lot 1: purchased at $100, held 400 days (long-term)
                TaxLot(shares=Decimal("5"), cost_basis=Decimal("100"), purchase_date=now),
                # Lot 2: purchased at $110, held 100 days (short-term)
                TaxLot(
                    shares=Decimal("5"),
                    cost_basis=Decimal("110"),
                    purchase_date=now + timedelta(days=300),
                ),
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])

        order = Order(action="sell", symbol="AAPL", amount=Decimal("8"), reasoning="Partial sell")

        # Sell 400 days after first purchase
        transaction = execute_sell(
            portfolio=portfolio,
            order=order,
            current_price=Decimal("120"),
            agent_id="agent_001",
            config=config,
            timestamp=now + timedelta(days=400),
        )

        # Lot 1: Sell all 5 shares (long-term)
        # Gain: 5 * ($120 - $100) = $100
        # Tax: $100 * 0.15 = $15

        # Lot 2: Sell 3 shares (short-term, 100 days)
        # Gain: 3 * ($120 - $110) = $30
        # Tax: $30 * 0.35 = $10.50

        # Total tax: $15 + $10.50 = $25.50
        # Net proceeds: $960 - $25.50 = $934.50

        assert transaction.shares == Decimal("8")
        assert transaction.gross_amount == Decimal("960")
        assert transaction.tax_amount == Decimal("25.50")
        assert transaction.net_amount == Decimal("934.50")

        assert len(transaction.lot_sales) == 2
        # Lot 1 (long-term)
        assert transaction.lot_sales[0].shares == Decimal("5")
        assert transaction.lot_sales[0].is_long_term
        assert transaction.lot_sales[0].tax_amount == Decimal("15")
        # Lot 2 (short-term)
        assert transaction.lot_sales[1].shares == Decimal("3")
        assert not transaction.lot_sales[1].is_long_term
        assert transaction.lot_sales[1].tax_amount == Decimal("10.50")

        # Portfolio should have 2 shares remaining from lot 2
        position = portfolio.get_position("AAPL")
        assert position.total_shares == Decimal("2")
        assert len(position.lots) == 1
        assert position.lots[0].shares == Decimal("2")

    def test_execute_sell_insufficient_shares_raises_error(self, config):
        """Test selling more shares than owned raises ValueError."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("5"), cost_basis=Decimal("100"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])

        order = Order(action="sell", symbol="AAPL", amount=Decimal("10"), reasoning="Too many")

        with pytest.raises(ValueError, match="Sell order validation failed"):
            execute_sell(
                portfolio=portfolio,
                order=order,
                current_price=Decimal("120"),
                agent_id="agent_001",
                config=config,
            )

    def test_execute_sell_nonexistent_position_raises_error(self, config):
        """Test selling nonexistent position raises ValueError."""
        portfolio = Portfolio(cash=Decimal("500"))
        order = Order(action="sell", symbol="AAPL", amount=Decimal("10"), reasoning="No position")

        with pytest.raises(ValueError, match="Sell order validation failed"):
            execute_sell(
                portfolio=portfolio,
                order=order,
                current_price=Decimal("120"),
                agent_id="agent_001",
                config=config,
            )


class TestExecuteOrder:
    """Tests for execute_order function."""

    def test_execute_order_dispatches_buy(self, config):
        """Test execute_order dispatches to execute_buy for buy orders."""
        portfolio = Portfolio(cash=Decimal("1000"))
        order = Order(action="buy", symbol="AAPL", amount=Decimal("500"), reasoning="Good buy")

        transaction = execute_order(
            portfolio=portfolio,
            order=order,
            current_price=Decimal("100"),
            agent_id="agent_001",
            config=config,
        )

        assert transaction.action == "buy"
        assert transaction.shares == Decimal("5")
        assert portfolio.cash == Decimal("500")

    def test_execute_order_dispatches_sell(self, config):
        """Test execute_order dispatches to execute_sell for sell orders."""
        now = datetime.now(timezone.utc)
        position = StockPosition(
            symbol="AAPL",
            lots=[
                TaxLot(shares=Decimal("10"), cost_basis=Decimal("100"), purchase_date=now)
            ],
        )
        portfolio = Portfolio(cash=Decimal("500"), positions=[position])
        order = Order(action="sell", symbol="AAPL", amount=Decimal("10"), reasoning="Good sell")

        transaction = execute_order(
            portfolio=portfolio,
            order=order,
            current_price=Decimal("120"),
            agent_id="agent_001",
            config=config,
            timestamp=now + timedelta(days=400),
        )

        assert transaction.action == "sell"
        assert transaction.shares == Decimal("10")
        assert portfolio.cash > Decimal("500")

    def test_order_rejects_invalid_action(self, config):
        """Test Order model rejects invalid action during construction."""
        from pydantic import ValidationError

        portfolio = Portfolio(cash=Decimal("1000"))

        # Pydantic validates the action field, so this raises ValidationError during Order creation
        with pytest.raises(ValidationError, match="Input should be 'buy' or 'sell'"):
            order = Order(
                action="hold",  # type: ignore
                symbol="AAPL",
                amount=Decimal("100"),
                reasoning="Invalid",
            )
