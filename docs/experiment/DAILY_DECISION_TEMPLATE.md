# Daily Trading Decision - {YYYY-MM-DD}

> **Agent**: {agent_name} ({agent_id})
> **Trading Day**: {day_number}
> **Market**: {market_status - Open/Pre-market/After-hours}

---

## Portfolio Summary

**Cash**: ${cash_amount}

**Positions**:
{for each position}
- **{SYMBOL}**: {shares} shares @ ${cost_basis} cost basis
  - Current price: ${current_price}
  - Position value: ${position_value}
  - Unrealized P/L: ${unrealized_pnl} ({unrealized_pnl_pct}%)
{endfor}

**Total Portfolio Value**: ${total_value}

**Performance**: {total_return_pct}% from starting capital

---

## Research Notes

{Agent's market analysis, stock research, and reasoning - this section should be comprehensive}

### Market Overview

{Brief assessment of overall market conditions}

**Example**: "Markets are mixed today with tech stocks showing weakness (-1.2% on Nasdaq) while financials are gaining (+0.8%). Fed minutes released yesterday suggest rates may stay higher for longer, putting pressure on growth stocks. Energy sector continues strength on rising oil prices."

### Stocks Researched

#### {SYMBOL_1}

**Current Price**: ${price}
**Market Cap**: ${market_cap}
**P/E Ratio**: {pe_ratio}
**52-Week Range**: ${low} - ${high}

**Fundamentals**:
- {Key fundamental observation 1}
- {Key fundamental observation 2}
- {Key fundamental observation 3}

**Recent News**:
- {News item 1 with date and source}
- {News item 2 with date and source}

**Technical Analysis**:
- {Technical observation - trend, support/resistance, momentum}

**Assessment**: {BUY / SELL / HOLD with brief reasoning}

#### {SYMBOL_2}

{Repeat same structure for each stock researched}

### Key Observations

{Bullet points of important observations}

**Example**:
- Tech earnings season wrapping up; most beats priced in already
- Financial stocks benefiting from higher rates environment
- Energy sector momentum continuing on supply constraints
- Healthcare showing relative strength as defensive play
- Small-cap stocks lagging large-caps significantly

---

## Trading Orders

{List all buy/sell orders - if no orders, explicitly state "No trades today" with reasoning}

### Order 1: BUY {SYMBOL}

**Action**: buy
**Symbol**: {TICKER}
**Amount**: ${dollar_amount}
**Estimated Shares**: ~{estimated_shares} shares (at current price ${current_price})

**Reasoning**:

{Detailed explanation for this trade - reference research above}

**Example**: "Buying $250 of AAPL. Stock has pulled back 5% from recent highs despite strong earnings beat last week, creating attractive entry point. P/E of 28 is reasonable for a mega-cap with AAPL's growth profile and ecosystem moat. Recent news of new product launches in AI space provides positive catalyst. This aligns with my thesis of buying quality tech on dips. Position will be ~20% of portfolio, within my 50% max position limit."

**Risk Factors**:
- {Risk 1}
- {Risk 2}

**Exit Plan**:
- Take partial profits at +15%
- Stop loss at -8%
- Re-evaluate if fundamentals change

---

### Order 2: SELL {SYMBOL}

**Action**: sell
**Symbol**: {TICKER}
**Amount**: {number_of_shares} shares
**Estimated Proceeds**: ~${estimated_proceeds} (at current price ${current_price})
**Estimated Tax**: ~${estimated_tax} (35% on ${estimated_gain} capital gain)
**Estimated Net Cash**: ~${estimated_net}

**Reasoning**:

{Detailed explanation for this trade}

**Example**: "Selling 3.5 shares of TSLA. Stock has rallied 25% from my entry point of $220, reaching my profit target of $275. Recent volatility and lack of positive catalysts suggest consolidation ahead. While fundamentals remain strong, technical indicators showing overbought conditions (RSI > 70). Taking profits here to lock in gains and reduce exposure to potential pullback. Net proceeds after 35% capital gains tax will be ~$895.12."

**Tax Calculation**:
- Cost basis: 3.5 shares × $220 = $770
- Sale proceeds: 3.5 shares × $275 = $962.50
- Capital gain: $962.50 - $770 = $192.50
- Tax (35%): $192.50 × 0.35 = $67.38
- Net cash: $962.50 - $67.38 = $895.12

**Outcome Analysis**:
- Total return on position: +25.0%
- Holding period: 7 trading days
- Tax drag: -3.0% (on position)
- Net return after tax: +22.0%

---

### Order 3: HOLD {SYMBOL}

**Action**: hold
**Symbol**: {TICKER}
**Current Position**: {shares} shares

**Reasoning**:

{Explanation for maintaining position}

**Example**: "Holding 5 shares of MSFT. Position is up 8% but not at profit target yet (+15%). Stock showing continued strength with positive momentum from cloud revenue growth. No signs of topping, and fundamentals remain solid. Will continue holding for additional upside."

---

## Strategy Updates

{Optional section - only include if adding new learning to strategy}

### New Learning

**Observation**: {What happened or was noticed}

**Outcome**: {How it turned out}

**Lesson**: {What to do differently going forward}

**Example**:

**Observation**: Bought tech stocks early in the day without checking broader market trend

**Outcome**: Positions immediately dropped 2-3% as market sold off in afternoon on Fed comments

**Lesson**: Check market trend and major news before entering positions. Consider waiting until 11am+ when day's direction is clearer. Especially important on days with major economic data or Fed speakers.

**Strategy Impact**: Will now implement rule to avoid buying in first hour of trading on days with scheduled Fed events or economic data releases.

---

## Decision Summary

**Total Orders**: {number}
- {number} BUY orders for ${total_buy_amount}
- {number} SELL orders for ~${total_sell_proceeds}
- {number} HOLD positions

**Expected Portfolio Changes**:
- Cash: ${current_cash} → ${expected_cash} ({change})
- Positions: {current_position_count} → {expected_position_count}
- Portfolio Value: ~${expected_total_value}

**Strategy Alignment**: {How do today's decisions align with overall strategy?}

**Risk Assessment**: {How do these trades affect portfolio risk?}

---

## Execution Notes

{This section is filled in by the coordinator after orders execute}

**Execution Status**: {Pending / Completed / Partial}

**Executed Transactions**:
- {Transaction 1}: {status - Executed / Rejected with reason}
- {Transaction 2}: {status}
- ...

**Final Portfolio Value**: ${actual_value}

**Notes**: {Any execution issues, rejected orders, or important events}

---

*Decision completed at {timestamp}*
*Execution time: {execution_time_ms} ms*
