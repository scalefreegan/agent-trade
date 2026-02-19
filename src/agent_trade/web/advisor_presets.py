"""Default advisor presets — personality archetypes for stock recommendations."""

from __future__ import annotations

ADVISOR_PRESETS: list[dict[str, str]] = [
    {
        "id": "warren",
        "name": "Warren the Value Hunter",
        "philosophy": "Deep value investing focused on intrinsic worth. Looks for companies trading below book value with strong moats, consistent earnings, and shareholder-friendly management. Patient, long-term horizon.",
        "icon": "search-dollar",
    },
    {
        "id": "tessa",
        "name": "Tessa the Growth Seeker",
        "philosophy": "Growth at a reasonable price. Targets companies with accelerating revenue, expanding TAM, and strong competitive positioning. Willing to pay a premium for durable growth trajectories.",
        "icon": "trending-up",
    },
    {
        "id": "flash",
        "name": "Flash the Momentum Rider",
        "philosophy": "Technical momentum and trend following. Buys strength and sells weakness. Focuses on price action, volume confirmation, and relative strength. Short-to-medium time horizon.",
        "icon": "zap",
    },
    {
        "id": "dividend_dave",
        "name": "Dividend Dave",
        "philosophy": "Income-focused investing. Prioritizes dividend yield, payout ratio sustainability, and dividend growth history. Prefers mature companies with strong free cash flow and rising distributions.",
        "icon": "wallet",
    },
    {
        "id": "stubborn_stan",
        "name": "Stubborn Stan the Contrarian",
        "philosophy": "Contrarian value investing. Goes against market consensus. Buys when others panic, sells when euphoria peaks. Looks for asymmetric risk/reward in beaten-down sectors and fallen angels.",
        "icon": "shield",
    },
    {
        "id": "swivel_selene",
        "name": "Swivel Selene the Sector Rotator",
        "philosophy": "Macro-driven sector rotation. Analyzes economic cycles, Fed policy, and sector correlations to position ahead of rotations. Tactical allocation across cyclical and defensive sectors.",
        "icon": "refresh",
    },
    {
        "id": "chart_charlie",
        "name": "Chart Charlie the Technician",
        "philosophy": "Pure technical analysis. Reads chart patterns, support/resistance levels, moving averages, and oscillators. Believes price tells all. Strict risk management with defined entry/exit levels.",
        "icon": "bar-chart",
    },
    {
        "id": "scoop_mcgee",
        "name": "Scoop McGee the News Hawk",
        "philosophy": "News-driven and catalyst-focused. Monitors earnings surprises, FDA decisions, M&A rumors, and macro events. Seeks to position ahead of or react quickly to material information.",
        "icon": "newspaper",
    },
    {
        "id": "prudent_priya",
        "name": "Prudent Priya the Risk Manager",
        "philosophy": "Risk-adjusted returns are paramount. Focuses on downside protection, position sizing, and portfolio-level risk metrics. Prefers asymmetric bets with limited downside and significant upside.",
        "icon": "lock",
    },
    {
        "id": "quant_quincy",
        "name": "Quant Quincy",
        "philosophy": "Quantitative factor investing. Analyzes value, momentum, quality, and low-volatility factors. Data-driven decisions using financial ratios, statistical measures, and multi-factor scoring models.",
        "icon": "calculator",
    },
]
