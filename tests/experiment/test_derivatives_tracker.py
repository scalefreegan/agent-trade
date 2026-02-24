"""Tests for derivatives portfolio tracking (options and futures)."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from agent_trade.experiment.derivatives_tracker import (
    add_futures_position,
    add_option_position,
    calculate_derivatives_metrics,
    close_futures_position,
    process_futures_expirations,
    process_option_expirations,
    remove_option_position,
    validate_futures_leverage,
    validate_options_limit,
)
from agent_trade.experiment.models import (
    FuturesPosition,
    OptionPosition,
    Portfolio,
    StockPosition,
    TaxLot,
)


# ==============================================================================
# Fixtures
# ==============================================================================


def make_portfolio(cash: str = "10000.00") -> Portfolio:
    """Create a basic portfolio with cash."""
    return Portfolio(cash=Decimal(cash))


def make_portfolio_with_stocks(cash: str = "5000.00") -> Portfolio:
    """Create a portfolio with cash and stock positions."""
    return Portfolio(
        cash=Decimal(cash),
        positions=[
            StockPosition(
                symbol="AAPL",
                lots=[
                    TaxLot(
                        shares=Decimal("10"),
                        cost_basis=Decimal("150.00"),
                        purchase_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    )
                ],
            )
        ],
    )


# ==============================================================================
# Option Position Tests
# ==============================================================================


class TestAddOptionPosition:
    def test_add_new_option_position(self):
        portfolio = make_portfolio()
        position = add_option_position(
            portfolio=portfolio,
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date=date(2026, 6, 20),
            contracts=2,
            premium_per_share=Decimal("5.00"),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )

        assert len(portfolio.option_positions) == 1
        assert position.underlying == "AAPL"
        assert position.contract_type == "call"
        assert position.contracts == 2
        assert position.total_premium == Decimal("1000.00")  # 5 * 100 * 2

    def test_add_to_existing_position_averages_premium(self):
        portfolio = make_portfolio()
        # First purchase
        add_option_position(
            portfolio=portfolio,
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date=date(2026, 6, 20),
            contracts=1,
            premium_per_share=Decimal("5.00"),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        # Second purchase at different premium
        add_option_position(
            portfolio=portfolio,
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date=date(2026, 6, 20),
            contracts=1,
            premium_per_share=Decimal("7.00"),
            opened_date=datetime(2026, 2, 15, tzinfo=timezone.utc),
        )

        assert len(portfolio.option_positions) == 1
        pos = portfolio.option_positions[0]
        assert pos.contracts == 2
        # Average premium: (500 + 700) / (100 * 2) = 6.00
        assert pos.premium_per_share == Decimal("6.00")

    def test_add_option_rejects_non_positive_contracts(self):
        portfolio = make_portfolio()
        with pytest.raises(ValueError, match="non-positive contracts"):
            add_option_position(
                portfolio=portfolio,
                underlying="AAPL",
                contract_type="call",
                strike_price=Decimal("200.00"),
                expiration_date=date(2026, 6, 20),
                contracts=0,
                premium_per_share=Decimal("5.00"),
                opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            )

    def test_add_option_rejects_negative_premium(self):
        portfolio = make_portfolio()
        with pytest.raises(ValueError, match="negative"):
            add_option_position(
                portfolio=portfolio,
                underlying="AAPL",
                contract_type="call",
                strike_price=Decimal("200.00"),
                expiration_date=date(2026, 6, 20),
                contracts=1,
                premium_per_share=Decimal("-1.00"),
                opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            )


class TestRemoveOptionPosition:
    def test_close_partial_option_position(self):
        portfolio = make_portfolio()
        add_option_position(
            portfolio=portfolio,
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date=date(2026, 6, 20),
            contracts=5,
            premium_per_share=Decimal("5.00"),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )

        key = portfolio.option_positions[0].position_key
        original = remove_option_position(portfolio, key, 2)

        assert original.contracts == 2
        assert len(portfolio.option_positions) == 1
        assert portfolio.option_positions[0].contracts == 3

    def test_close_full_option_position_removes_it(self):
        portfolio = make_portfolio()
        add_option_position(
            portfolio=portfolio,
            underlying="AAPL",
            contract_type="put",
            strike_price=Decimal("150.00"),
            expiration_date=date(2026, 6, 20),
            contracts=3,
            premium_per_share=Decimal("4.00"),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )

        key = portfolio.option_positions[0].position_key
        remove_option_position(portfolio, key, 3)

        assert len(portfolio.option_positions) == 0

    def test_close_option_rejects_insufficient_contracts(self):
        portfolio = make_portfolio()
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

        key = portfolio.option_positions[0].position_key
        with pytest.raises(ValueError, match="Insufficient contracts"):
            remove_option_position(portfolio, key, 5)

    def test_close_option_rejects_nonexistent_key(self):
        portfolio = make_portfolio()
        with pytest.raises(ValueError, match="not found"):
            remove_option_position(portfolio, "FAKE_KEY", 1)


class TestOptionExpirations:
    def test_itm_call_expires_with_cash_settlement(self):
        portfolio = make_portfolio("10000.00")
        add_option_position(
            portfolio=portfolio,
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("150.00"),
            expiration_date=date(2026, 2, 20),
            contracts=1,
            premium_per_share=Decimal("5.00"),
            opened_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        prices = {"AAPL": Decimal("200.00")}  # ITM by $50
        expired = process_option_expirations(portfolio, date(2026, 2, 20), prices)

        assert len(expired) == 1
        opt, settlement = expired[0]
        # Intrinsic value: (200 - 150) * 100 * 1 = $5000
        assert settlement == Decimal("5000")
        assert len(portfolio.option_positions) == 0
        assert portfolio.cash == Decimal("15000.00")  # 10000 + 5000

    def test_otm_call_expires_worthless(self):
        portfolio = make_portfolio("10000.00")
        add_option_position(
            portfolio=portfolio,
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date=date(2026, 2, 20),
            contracts=1,
            premium_per_share=Decimal("5.00"),
            opened_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        prices = {"AAPL": Decimal("180.00")}  # OTM
        expired = process_option_expirations(portfolio, date(2026, 2, 20), prices)

        assert len(expired) == 1
        _, settlement = expired[0]
        assert settlement == Decimal("0")
        assert len(portfolio.option_positions) == 0
        assert portfolio.cash == Decimal("10000.00")  # Unchanged

    def test_non_expired_options_untouched(self):
        portfolio = make_portfolio()
        add_option_position(
            portfolio=portfolio,
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("200.00"),
            expiration_date=date(2026, 6, 20),
            contracts=1,
            premium_per_share=Decimal("5.00"),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )

        prices = {"AAPL": Decimal("250.00")}
        expired = process_option_expirations(portfolio, date(2026, 2, 20), prices)

        assert len(expired) == 0
        assert len(portfolio.option_positions) == 1


# ==============================================================================
# Futures Position Tests
# ==============================================================================


class TestAddFuturesPosition:
    def test_open_long_futures_position(self):
        portfolio = make_portfolio("50000.00")
        position = add_futures_position(
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

        assert len(portfolio.futures_positions) == 1
        assert position.direction == "long"
        assert position.contracts == 1
        assert position.notional_value == Decimal("250000.00")
        assert portfolio.cash == Decimal("38000.00")  # 50000 - 12000
        assert portfolio.margin_used == Decimal("12000.00")

    def test_open_futures_rejects_insufficient_margin(self):
        portfolio = make_portfolio("5000.00")
        with pytest.raises(ValueError, match="Insufficient cash for margin"):
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

    def test_open_futures_rejects_non_positive_contracts(self):
        portfolio = make_portfolio("50000.00")
        with pytest.raises(ValueError, match="non-positive"):
            add_futures_position(
                portfolio=portfolio,
                symbol="ES",
                direction="long",
                contracts=0,
                entry_price=Decimal("5000.00"),
                contract_multiplier=Decimal("50"),
                expiration_date=date(2026, 6, 20),
                opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
                margin_per_contract=Decimal("12000.00"),
            )


class TestCloseFuturesPosition:
    def test_close_with_profit(self):
        portfolio = make_portfolio("50000.00")
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
        # Cash is now 38000, margin_used is 12000

        key = portfolio.futures_positions[0].position_key
        snapshot, pnl = close_futures_position(
            portfolio, key, 1, Decimal("5100.00")  # +100 points
        )

        # P&L: (5100 - 5000) * 50 * 1 = $5000
        assert pnl == Decimal("5000")
        assert len(portfolio.futures_positions) == 0
        assert portfolio.margin_used == Decimal("0")
        # Cash: 38000 + 12000 (margin) + 5000 (P&L) = 55000
        assert portfolio.cash == Decimal("55000")

    def test_close_with_loss(self):
        portfolio = make_portfolio("50000.00")
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

        key = portfolio.futures_positions[0].position_key
        snapshot, pnl = close_futures_position(
            portfolio, key, 1, Decimal("4900.00")  # -100 points
        )

        # P&L: (4900 - 5000) * 50 * 1 = -$5000
        assert pnl == Decimal("-5000")
        # Cash: 38000 + 12000 (margin) + (-5000) (P&L) = 45000
        assert portfolio.cash == Decimal("45000")

    def test_close_short_with_profit(self):
        portfolio = make_portfolio("50000.00")
        add_futures_position(
            portfolio=portfolio,
            symbol="ES",
            direction="short",
            contracts=1,
            entry_price=Decimal("5000.00"),
            contract_multiplier=Decimal("50"),
            expiration_date=date(2026, 6, 20),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            margin_per_contract=Decimal("12000.00"),
        )

        key = portfolio.futures_positions[0].position_key
        snapshot, pnl = close_futures_position(
            portfolio, key, 1, Decimal("4900.00")  # Price went down = profit for short
        )

        # P&L for short: -(4900 - 5000) * 50 * 1 = $5000
        assert pnl == Decimal("5000")

    def test_partial_close(self):
        portfolio = make_portfolio("100000.00")
        add_futures_position(
            portfolio=portfolio,
            symbol="ES",
            direction="long",
            contracts=3,
            entry_price=Decimal("5000.00"),
            contract_multiplier=Decimal("50"),
            expiration_date=date(2026, 6, 20),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            margin_per_contract=Decimal("12000.00"),
        )
        # Cash: 100000 - 36000 = 64000

        key = portfolio.futures_positions[0].position_key
        snapshot, pnl = close_futures_position(
            portfolio, key, 1, Decimal("5050.00")
        )

        assert snapshot.contracts == 1
        assert pnl == Decimal("2500")  # (5050-5000)*50*1
        assert len(portfolio.futures_positions) == 1
        assert portfolio.futures_positions[0].contracts == 2
        assert portfolio.margin_used == Decimal("24000.00")  # 2 * 12000


class TestFuturesExpirations:
    def test_expired_futures_settled_and_removed(self):
        portfolio = make_portfolio("50000.00")
        add_futures_position(
            portfolio=portfolio,
            symbol="ES",
            direction="long",
            contracts=1,
            entry_price=Decimal("5000.00"),
            contract_multiplier=Decimal("50"),
            expiration_date=date(2026, 2, 20),
            opened_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            margin_per_contract=Decimal("12000.00"),
        )
        # Cash: 38000, margin: 12000

        prices = {"ES": Decimal("5200.00")}
        expired = process_futures_expirations(portfolio, date(2026, 2, 20), prices)

        assert len(expired) == 1
        _, pnl = expired[0]
        # P&L: (5200 - 5000) * 50 * 1 = $10000
        assert pnl == Decimal("10000")
        assert len(portfolio.futures_positions) == 0
        assert portfolio.margin_used == Decimal("0")
        # Cash: 38000 + 12000 (margin) + 10000 (P&L) = 60000
        assert portfolio.cash == Decimal("60000")


# ==============================================================================
# Validation Tests
# ==============================================================================


class TestValidateOptionsLimit:
    def test_within_limit(self):
        portfolio = make_portfolio_with_stocks("5000.00")
        prices = {"AAPL": Decimal("200.00")}
        # Portfolio value ~= 5000 + 10*200 = 7000
        # 20% of 7000 = 1400
        valid, error = validate_options_limit(
            portfolio, Decimal("500.00"), prices, Decimal("0.20")
        )
        assert valid is True
        assert error is None

    def test_exceeds_limit(self):
        portfolio = make_portfolio_with_stocks("5000.00")
        prices = {"AAPL": Decimal("200.00")}
        # Portfolio value = 7000, 20% = 1400
        valid, error = validate_options_limit(
            portfolio, Decimal("2000.00"), prices, Decimal("0.20")
        )
        assert valid is False
        assert "limit exceeded" in error


class TestValidateFuturesLeverage:
    def test_within_leverage(self):
        portfolio = make_portfolio("50000.00")
        prices = {}
        valid, error = validate_futures_leverage(
            portfolio, Decimal("100000.00"), prices, Decimal("5.0")
        )
        assert valid is True

    def test_exceeds_leverage(self):
        portfolio = make_portfolio("10000.00")
        prices = {}
        valid, error = validate_futures_leverage(
            portfolio, Decimal("60000.00"), prices, Decimal("5.0")
        )
        assert valid is False
        assert "leverage exceeded" in error


# ==============================================================================
# Metrics Tests
# ==============================================================================


class TestDerivativesMetrics:
    def test_metrics_with_options_and_futures(self):
        portfolio = make_portfolio("20000.00")
        add_option_position(
            portfolio=portfolio,
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("150.00"),
            expiration_date=date(2026, 6, 20),
            contracts=2,
            premium_per_share=Decimal("5.00"),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        add_futures_position(
            portfolio=portfolio,
            symbol="ES",
            direction="long",
            contracts=1,
            entry_price=Decimal("5000.00"),
            contract_multiplier=Decimal("50"),
            expiration_date=date(2026, 6, 20),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            margin_per_contract=Decimal("5000.00"),
        )

        prices = {"AAPL": Decimal("200.00"), "ES": Decimal("5100.00")}
        metrics = calculate_derivatives_metrics(portfolio, prices)

        assert metrics["options_count"] == Decimal("1")
        assert metrics["options_premium_invested"] == Decimal("1000.00")
        # Intrinsic: (200-150) * 100 * 2 = 10000
        assert metrics["options_intrinsic_value"] == Decimal("10000")
        assert metrics["options_pnl"] == Decimal("9000")  # 10000 - 1000

        assert metrics["futures_count"] == Decimal("1")
        assert metrics["futures_notional"] == Decimal("250000.00")
        # Unrealized P&L: (5100-5000)*50*1 = 5000
        assert metrics["futures_unrealized_pnl"] == Decimal("5000")


# ==============================================================================
# Portfolio total_value with derivatives
# ==============================================================================


class TestPortfolioValueWithDerivatives:
    def test_portfolio_value_includes_options(self):
        portfolio = make_portfolio("10000.00")
        add_option_position(
            portfolio=portfolio,
            underlying="AAPL",
            contract_type="call",
            strike_price=Decimal("150.00"),
            expiration_date=date(2026, 6, 20),
            contracts=1,
            premium_per_share=Decimal("5.00"),
            opened_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )

        prices = {"AAPL": Decimal("200.00")}
        # Cash: 10000
        # Option intrinsic: (200-150)*100*1 = 5000
        total = portfolio.total_value(prices, strict=False)
        assert total == Decimal("15000.00")

    def test_portfolio_value_includes_futures_pnl(self):
        portfolio = make_portfolio("50000.00")
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
        # Cash now: 38000, margin_used: 12000

        prices = {"ES": Decimal("5100.00")}
        # Cash: 38000
        # Futures P&L: (5100-5000)*50*1 = 5000
        total = portfolio.total_value(prices, strict=False)
        assert total == Decimal("43000.00")
