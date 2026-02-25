"""Tests for derivatives transaction processing (options and futures)."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from agent_trade.experiment.derivatives_processor import (
    execute_futures_close,
    execute_futures_open,
    execute_option_buy,
    execute_option_order,
    execute_option_sell,
)
from agent_trade.experiment.derivatives_tracker import add_option_position
from agent_trade.experiment.models import (
    ExperimentConfig,
    FuturesOrder,
    OptionOrder,
    Portfolio,
)


# ==============================================================================
# Fixtures
# ==============================================================================


def make_config(**overrides) -> ExperimentConfig:
    """Create an experiment config for testing."""
    defaults = dict(
        experiment_id="test_exp",
        name="Test Experiment",
        num_agents=1,
        starting_capital=Decimal("10000.00"),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status="active",
        trading_mode="multi_instrument",
        options_enabled=True,
        futures_enabled=True,
        max_options_pct=Decimal("0.20"),
        max_futures_leverage=Decimal("5.0"),
        min_trade_amount=Decimal("1.00"),
    )
    defaults.update(overrides)
    return ExperimentConfig(**defaults)


def make_portfolio(cash: str = "10000.00") -> Portfolio:
    """Create a basic portfolio."""
    return Portfolio(cash=Decimal(cash))


# ==============================================================================
# Option Buy Tests
# ==============================================================================


class TestExecuteOptionBuy:
    def test_buy_call_options(self):
        portfolio = make_portfolio("10000.00")
        config = make_config()
        order = OptionOrder(
            action="buy_to_open",
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date="2026-06-20",
            contracts=2,
            reasoning="Bullish on AAPL",
        )

        prices = {"AAPL": Decimal("190.00")}
        txn = execute_option_buy(
            portfolio, order, Decimal("5.00"), "agent_001", config, prices
        )

        assert txn.action == "buy_to_open"
        assert txn.underlying == "AAPL"
        assert txn.contracts == 2
        assert txn.total_premium == Decimal("1000.00")  # 5 * 100 * 2
        assert txn.net_amount == Decimal("-1000.00")
        assert len(portfolio.option_positions) == 1
        assert portfolio.cash == Decimal("9000.00")

    def test_buy_put_options(self):
        portfolio = make_portfolio("10000.00")
        config = make_config()
        order = OptionOrder(
            action="buy_to_open",
            underlying="TSLA",
            contract_type="put",
            strike_price=Decimal("300.00"),
            expiration_date="2026-03-20",
            contracts=1,
            reasoning="Bearish on TSLA",
        )

        prices = {"TSLA": Decimal("320.00")}
        txn = execute_option_buy(
            portfolio, order, Decimal("8.50"), "agent_001", config, prices
        )

        assert txn.contract_type == "put"
        assert txn.total_premium == Decimal("850.00")

    def test_buy_fails_insufficient_cash(self):
        portfolio = make_portfolio("100.00")
        config = make_config()
        order = OptionOrder(
            action="buy_to_open",
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date="2026-06-20",
            contracts=5,
            reasoning="Bullish",
        )

        prices = {"AAPL": Decimal("190.00")}
        with pytest.raises(ValueError, match="Insufficient cash"):
            execute_option_buy(
                portfolio, order, Decimal("5.00"), "agent_001", config, prices
            )


# ==============================================================================
# Option Sell Tests
# ==============================================================================


class TestExecuteOptionSell:
    def test_sell_option_with_profit(self):
        portfolio = make_portfolio("10000.00")
        config = make_config()

        # First buy some options
        add_option_position(
            portfolio=portfolio,
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date=date(2026, 6, 20),
            contracts=2,
            premium_per_share=Decimal("5.00"),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )

        order = OptionOrder(
            action="sell_to_close",
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date="2026-06-20",
            contracts=1,
            reasoning="Taking profits",
        )

        txn = execute_option_sell(
            portfolio, order, Decimal("8.00"), "agent_001", config
        )

        assert txn.action == "sell_to_close"
        assert txn.contracts == 1
        assert txn.total_premium == Decimal("800.00")  # 8 * 100 * 1
        # P&L: (8 - 5) * 100 * 1 = $300
        assert txn.realized_pnl == Decimal("300.00")
        assert portfolio.cash == Decimal("10800.00")
        assert portfolio.option_positions[0].contracts == 1

    def test_sell_fails_no_position(self):
        portfolio = make_portfolio("10000.00")
        config = make_config()

        order = OptionOrder(
            action="sell_to_close",
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date="2026-06-20",
            contracts=1,
            reasoning="Close",
        )

        with pytest.raises(ValueError, match="not found"):
            execute_option_sell(
                portfolio, order, Decimal("8.00"), "agent_001", config
            )


# ==============================================================================
# Option Order Dispatch Tests
# ==============================================================================


class TestExecuteOptionOrder:
    def test_dispatches_buy_to_open(self):
        portfolio = make_portfolio("10000.00")
        config = make_config()
        order = OptionOrder(
            action="buy_to_open",
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date="2026-06-20",
            contracts=1,
            reasoning="Bullish",
        )

        prices = {"AAPL": Decimal("190.00")}
        txn = execute_option_order(
            portfolio, order, Decimal("5.00"), "agent_001", config, prices
        )
        assert txn.action == "buy_to_open"

    def test_dispatches_sell_to_close(self):
        portfolio = make_portfolio("10000.00")
        config = make_config()

        # Add a position first
        add_option_position(
            portfolio=portfolio,
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date=date(2026, 6, 20),
            contracts=2,
            premium_per_share=Decimal("5.00"),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )

        order = OptionOrder(
            action="sell_to_close",
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date="2026-06-20",
            contracts=1,
            reasoning="Close",
        )

        prices = {"AAPL": Decimal("190.00")}
        txn = execute_option_order(
            portfolio, order, Decimal("6.00"), "agent_001", config, prices
        )
        assert txn.action == "sell_to_close"


# ==============================================================================
# Futures Open Tests
# ==============================================================================


class TestExecuteFuturesOpen:
    def test_open_long_futures(self):
        portfolio = make_portfolio("50000.00")
        config = make_config()
        order = FuturesOrder(
            action="open_long",
            symbol="ES",
            contracts=1,
            reasoning="Bullish S&P 500",
        )

        prices = {"ES": Decimal("5000.00")}
        txn = execute_futures_open(
            portfolio, order,
            current_price=Decimal("5000.00"),
            contract_multiplier=Decimal("50"),
            margin_per_contract=Decimal("12000.00"),
            expiration_date=date(2026, 6, 20),
            agent_id="agent_001",
            config=config,
            current_prices=prices,
        )

        assert txn.action == "open_long"
        assert txn.contracts == 1
        assert txn.margin_impact == Decimal("12000.00")
        assert len(portfolio.futures_positions) == 1
        assert portfolio.cash == Decimal("38000.00")
        assert portfolio.margin_used == Decimal("12000.00")

    def test_open_short_futures(self):
        portfolio = make_portfolio("500000.00")  # Large enough for NQ leverage
        config = make_config()
        order = FuturesOrder(
            action="open_short",
            symbol="NQ",
            contracts=1,
            reasoning="Bearish tech",
        )

        prices = {"NQ": Decimal("18000.00")}
        txn = execute_futures_open(
            portfolio, order,
            current_price=Decimal("18000.00"),
            contract_multiplier=Decimal("20"),
            margin_per_contract=Decimal("16000.00"),
            expiration_date=date(2026, 6, 20),
            agent_id="agent_001",
            config=config,
            current_prices=prices,
        )

        assert txn.action == "open_short"
        assert portfolio.futures_positions[0].direction == "short"

    def test_open_fails_insufficient_margin(self):
        portfolio = make_portfolio("5000.00")
        config = make_config()
        order = FuturesOrder(
            action="open_long",
            symbol="ES",
            contracts=1,
            reasoning="Bullish",
        )

        prices = {"ES": Decimal("5000.00")}
        with pytest.raises(ValueError, match="Insufficient margin"):
            execute_futures_open(
                portfolio, order,
                current_price=Decimal("5000.00"),
                contract_multiplier=Decimal("50"),
                margin_per_contract=Decimal("12000.00"),
                expiration_date=date(2026, 6, 20),
                agent_id="agent_001",
                config=config,
                current_prices=prices,
            )


# ==============================================================================
# Futures Close Tests
# ==============================================================================


class TestExecuteFuturesClose:
    def test_close_with_profit(self):
        portfolio = make_portfolio("50000.00")
        config = make_config()

        # Open position first
        from agent_trade.experiment.derivatives_tracker import add_futures_position
        add_futures_position(
            portfolio=portfolio,
            symbol="ES",
            direction="long",
            contracts=1,
            entry_price=Decimal("5000.00"),
            contract_multiplier=Decimal("50"),
            expiration_date=date(2026, 6, 20),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            margin_per_contract=Decimal("12000.00"),
        )

        order = FuturesOrder(
            action="close",
            symbol="ES",
            contracts=1,
            reasoning="Taking profits",
        )

        txn = execute_futures_close(
            portfolio, order, Decimal("5100.00"), "agent_001", config
        )

        assert txn.action == "close"
        assert txn.realized_pnl == Decimal("5000")  # (5100-5000)*50
        assert len(portfolio.futures_positions) == 0

    def test_close_fails_no_position(self):
        portfolio = make_portfolio("50000.00")
        config = make_config()

        order = FuturesOrder(
            action="close",
            symbol="ES",
            contracts=1,
            reasoning="Close",
        )

        with pytest.raises(ValueError, match="No open futures position"):
            execute_futures_close(
                portfolio, order, Decimal("5000.00"), "agent_001", config
            )


# ==============================================================================
# Model Validation Tests
# ==============================================================================


class TestOptionOrderValidation:
    def test_validate_buy_success(self):
        order = OptionOrder(
            action="buy_to_open",
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date="2026-06-20",
            contracts=1,
            reasoning="Test",
        )
        valid, error = order.validate_buy(
            Decimal("10000.00"), Decimal("5.00"), Decimal("1.00")
        )
        assert valid is True
        assert error is None

    def test_validate_buy_insufficient_cash(self):
        order = OptionOrder(
            action="buy_to_open",
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date="2026-06-20",
            contracts=5,
            reasoning="Test",
        )
        valid, error = order.validate_buy(
            Decimal("100.00"), Decimal("5.00"), Decimal("1.00")
        )
        assert valid is False
        assert "Insufficient cash" in error

    def test_validate_sell_success(self):
        order = OptionOrder(
            action="sell_to_close",
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date="2026-06-20",
            contracts=2,
            reasoning="Test",
        )
        valid, error = order.validate_sell(5)
        assert valid is True

    def test_validate_sell_insufficient_contracts(self):
        order = OptionOrder(
            action="sell_to_close",
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date="2026-06-20",
            contracts=5,
            reasoning="Test",
        )
        valid, error = order.validate_sell(2)
        assert valid is False


class TestFuturesOrderValidation:
    def test_validate_open_success(self):
        order = FuturesOrder(
            action="open_long",
            symbol="ES",
            contracts=1,
            reasoning="Test",
        )
        valid, error = order.validate_open(
            Decimal("50000.00"), Decimal("12000.00")
        )
        assert valid is True

    def test_validate_open_insufficient_margin(self):
        order = FuturesOrder(
            action="open_long",
            symbol="ES",
            contracts=1,
            reasoning="Test",
        )
        valid, error = order.validate_open(
            Decimal("5000.00"), Decimal("12000.00")
        )
        assert valid is False
        assert "Insufficient margin" in error

    def test_validate_close_success(self):
        order = FuturesOrder(
            action="close",
            symbol="ES",
            contracts=1,
            reasoning="Test",
        )
        valid, error = order.validate_close(3)
        assert valid is True

    def test_validate_close_insufficient_contracts(self):
        order = FuturesOrder(
            action="close",
            symbol="ES",
            contracts=5,
            reasoning="Test",
        )
        valid, error = order.validate_close(2)
        assert valid is False


# ==============================================================================
# Option/Futures Position Model Tests
# ==============================================================================


class TestOptionPositionModel:
    def test_intrinsic_value_call_itm(self):
        from agent_trade.experiment.models import OptionPosition
        opt = OptionPosition(
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("150.00"),
            expiration_date=date(2026, 6, 20),
            contracts=1,
            premium_per_share=Decimal("5.00"),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        assert opt.intrinsic_value(Decimal("200.00")) == Decimal("50.00")
        assert opt.total_intrinsic_value(Decimal("200.00")) == Decimal("5000")

    def test_intrinsic_value_call_otm(self):
        from agent_trade.experiment.models import OptionPosition
        opt = OptionPosition(
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date=date(2026, 6, 20),
            contracts=1,
            premium_per_share=Decimal("5.00"),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        assert opt.intrinsic_value(Decimal("150.00")) == Decimal("0")

    def test_intrinsic_value_put_itm(self):
        from agent_trade.experiment.models import OptionPosition
        opt = OptionPosition(
            underlying="AAPL",
            contract_type="put",
            strike_price=Decimal("200.00"),
            expiration_date=date(2026, 6, 20),
            contracts=2,
            premium_per_share=Decimal("5.00"),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        assert opt.intrinsic_value(Decimal("150.00")) == Decimal("50.00")
        assert opt.total_intrinsic_value(Decimal("150.00")) == Decimal("10000")

    def test_is_expired(self):
        from agent_trade.experiment.models import OptionPosition
        opt = OptionPosition(
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date=date(2026, 3, 20),
            contracts=1,
            premium_per_share=Decimal("5.00"),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        assert opt.is_expired(date(2026, 3, 19)) is False
        assert opt.is_expired(date(2026, 3, 20)) is True
        assert opt.is_expired(date(2026, 3, 21)) is True

    def test_position_key(self):
        from agent_trade.experiment.models import OptionPosition
        opt = OptionPosition(
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date=date(2026, 6, 20),
            contracts=1,
            premium_per_share=Decimal("5.00"),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        assert opt.position_key == "AAPL_call_200.00_2026-06-20"


class TestFuturesPositionModel:
    def test_unrealized_pnl_long(self):
        from agent_trade.experiment.models import FuturesPosition
        fut = FuturesPosition(
            symbol="ES",
            direction="long",
            contracts=2,
            entry_price=Decimal("5000.00"),
            contract_multiplier=Decimal("50"),
            expiration_date=date(2026, 6, 20),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            margin_per_contract=Decimal("12000.00"),
        )
        # (5100 - 5000) * 50 * 2 = $10000
        assert fut.unrealized_pnl(Decimal("5100.00")) == Decimal("10000")
        # (4900 - 5000) * 50 * 2 = -$10000
        assert fut.unrealized_pnl(Decimal("4900.00")) == Decimal("-10000")

    def test_unrealized_pnl_short(self):
        from agent_trade.experiment.models import FuturesPosition
        fut = FuturesPosition(
            symbol="ES",
            direction="short",
            contracts=1,
            entry_price=Decimal("5000.00"),
            contract_multiplier=Decimal("50"),
            expiration_date=date(2026, 6, 20),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            margin_per_contract=Decimal("12000.00"),
        )
        # Short: -(5100 - 5000) * 50 * 1 = -$5000
        assert fut.unrealized_pnl(Decimal("5100.00")) == Decimal("-5000")
        # Short: -(4900 - 5000) * 50 * 1 = $5000
        assert fut.unrealized_pnl(Decimal("4900.00")) == Decimal("5000")

    def test_notional_value(self):
        from agent_trade.experiment.models import FuturesPosition
        fut = FuturesPosition(
            symbol="ES",
            direction="long",
            contracts=2,
            entry_price=Decimal("5000.00"),
            contract_multiplier=Decimal("50"),
            expiration_date=date(2026, 6, 20),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            margin_per_contract=Decimal("12000.00"),
        )
        assert fut.notional_value == Decimal("500000.00")

    def test_is_expired(self):
        from agent_trade.experiment.models import FuturesPosition
        fut = FuturesPosition(
            symbol="ES",
            direction="long",
            contracts=1,
            entry_price=Decimal("5000.00"),
            contract_multiplier=Decimal("50"),
            expiration_date=date(2026, 3, 20),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            margin_per_contract=Decimal("12000.00"),
        )
        assert fut.is_expired(date(2026, 3, 19)) is False
        assert fut.is_expired(date(2026, 3, 20)) is True
