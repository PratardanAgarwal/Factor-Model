# Methodology — The Nifty 500 Multi-Factor Model

*A plain-English companion to [`factor_calc.py`](./factor_calc.py), which contains the exact math. Educational only — not investment advice, and I am not a SEBI-registered adviser or research analyst.*

---

## What the model does

Every quarter it scores all ~500 companies in the Nifty 500 on four measurable traits, blends those into one score, and buys the best two dozen — spread across the economy so no single theme can dominate. It does **not** time the market. It does not predict. It buys measurable characteristics that have, over long periods, tended to pay off.

The weights and rules below are **fixed in advance and deliberately round** — they were not tuned to maximise a back-test, because a curve-fit that looks great on history usually fails live.

---

## The four factors

### Quality — *is this a good business?* (30% of the score)
| Component | Weight | Definition |
|---|---|---|
| Return on equity | 50% | Profit generated per rupee of shareholder capital. |
| Low debt | 35% | Debt-to-equity, **ranked within the industry** and **switched off for banks/financials** (10× leverage is normal for a bank, near-fatal for a paint company). |
| Positive earnings | 15% | A simple gate: the company actually made money last quarter. |

### Value — *am I paying a sensible price?* (25%)
| Component | Weight | Definition |
|---|---|---|
| Cheap P/E | 35% | Price ÷ earnings, **relative to the stock's own industry average.** |
| Cheap P/B | 30% | Price ÷ book value, sector-relative. |
| Cheap P/S | 20% | Price ÷ sales, sector-relative. |
| Dividend yield | 15% | Cash actually returned to shareholders. |

Everything is **sector-relative** on purpose: IT structurally trades at P/E 30, PSU banks at P/E 8. Comparing them head-on would make the screen buy nothing but banks forever. The right question is *"cheap versus companies like it?"*

### Momentum — *is the market already onto it?* (25%)
| Component | Weight | Definition |
|---|---|---|
| 12-minus-1 return | 85% | Last 12 months' price return, **excluding the most recent month** (very short-term moves tend to reverse — stripping the last month is standard practice). |
| Short-term reversal | 15% | A small contrarian nudge toward stocks that dipped recently. |

### Growth — *are the fundamentals improving?* (20%)
| Component | Weight | Definition |
|---|---|---|
| EPS year-on-year | 65% | This quarter vs the same quarter last year (neutralises seasonality). |
| EPS quarter-on-quarter | 35% | The more recent, noisier signal. |

---

## How scoring works

1. **Percentile-rank every raw number** to 0–1 (e.g. 0.90 = better than 90% of the universe). Percentiles are used instead of z-scores because they're immune to outliers (a P/E of 700 just ranks last and moves on).
2. **Blend into factor scores** using the sub-weights above.
3. **Blend into one composite:** `0.30·Quality + 0.25·Value + 0.25·Momentum + 0.20·Growth`.
4. **Apply the rules** (below), best-to-worst, until the book is full.

## The rules (diversification & liquidity)

- Target **up to 22** stocks, **equal-weighted** (equal rupees each — the highest-scored name is also where estimation error is largest, so don't overbet it). The actual count is an *output* of the rules, not a fixed number: the diversification caps and eligibility gates can leave fewer (**18** in the latest rebalance).
- Max **2 per industry**; max **6 per macro sector** — the macro cap is the single most important rule; without it the raw screen once put ~45% into commodities & utilities, which all move on the same driver.
- **Minimum market cap** floor for liquidity; must have **positive ROE and positive latest-quarter earnings**.

---

## What this is *not*

- **Not back-tested stock-by-stock** — point-in-time Indian fundamental history is expensive; this particular implementation is unproven, so the live, dated record is the real test.
- **Not a market-timing system** — an earlier timing model was validated and failed (it ranked ~29th percentile vs random signals), so timing was dropped entirely.
- **Not advice.** Factors underperform for years at a stretch; value traps and crowding are real risks. Do your own research or consult a registered professional.

---

## Reproduce it

`factor_calc.py` runs the entire calculation on a small dummy dataset with no external libraries. Swap in your own rows (same fields) and it scores them identically. The underlying Nifty 500 fundamentals dataset is not published (licensed input), but the **math is fully open** — check it, break it, tell me what's wrong.
