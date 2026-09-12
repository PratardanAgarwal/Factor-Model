"""
factor_calc.py  —  Nifty 500 multi-factor stock model: the scoring math, in the open.
================================================================================

This is the EXACT logic the model uses to turn raw fundamentals into a ranked
buy-list. It is published so anyone can check the math. It does NOT include the
underlying fundamentals dataset (that is licensed / the author's input) — instead
it runs on a tiny DUMMY dataset below so the calculation is fully reproducible.

Plug your own rows into STOCKS (same fields) and it will score them identically.

No third-party libraries required — plain Python 3.

Author: Pratardan · personal systematic-investing experiment · 2026
DISCLAIMER: Educational only. Not investment advice. Not SEBI-registered.
================================================================================
"""

# -----------------------------------------------------------------------------
# 0. FACTOR WEIGHTS & RULES  (the model's fixed configuration)
# -----------------------------------------------------------------------------
WEIGHTS = {"quality": 0.30, "value": 0.25, "momentum": 0.25, "growth": 0.20}  # sum = 1.0

RULES = {
    "n_stocks":        5,     # how many to hold (real model: 22)
    "max_per_industry": 2,    # no more than 2 from one industry
    "max_per_macro":    6,    # no more than 6 from one macro sector
    "min_mcap_cr":      5000, # liquidity floor, in Rs crore
}

# sub-weights inside each factor
QUALITY_W = {"roe": 0.50, "low_debt": 0.35, "earnings_positive": 0.15}
VALUE_W   = {"cheap_pe": 0.35, "cheap_pb": 0.30, "cheap_ps": 0.20, "div_yield": 0.15}
MOMENTUM_W = {"mom_12_1": 0.85, "reversal": 0.15}
GROWTH_W   = {"eps_yoy": 0.65, "eps_qoq": 0.35}


# -----------------------------------------------------------------------------
# 1. HELPERS
# -----------------------------------------------------------------------------
def percentile_rank(values):
    """Return each value's percentile (0..1): fraction of the universe below it.
    Robust to outliers (unlike z-scores) — this is why the model uses percentiles."""
    n = len(values)
    out = []
    for v in values:
        below = sum(1 for x in values if x < v)
        out.append(below / (n - 1) if n > 1 else 0.5)
    return out


def sector_relative(rows, field):
    """Divide each stock's ratio by its OWN industry's average, so an IT stock at
    P/E 30 isn't punished vs a PSU bank at P/E 8. Returns the relative ratio."""
    sums, counts = {}, {}
    for r in rows:
        s = r["industry"]
        sums[s] = sums.get(s, 0) + r[field]
        counts[s] = counts.get(s, 0) + 1
    return [r[field] / (sums[r["industry"]] / counts[r["industry"]]) for r in rows]


# -----------------------------------------------------------------------------
# 2. THE FOUR FACTOR SCORES  (each returns a 0..1 score per stock)
# -----------------------------------------------------------------------------
def quality(rows):
    roe_p = percentile_rank([r["roe"] for r in rows])
    # low debt: lower D/E is better -> invert; debt is switched OFF for financials
    de = [r["de"] for r in rows]
    de_p = percentile_rank(de)
    low_debt = [0.5 if r["is_financial"] else (1 - p) for r, p in zip(rows, de_p)]
    earn_pos = [1.0 if r["eps_latest"] > 0 else 0.0 for r in rows]
    return [QUALITY_W["roe"]*q + QUALITY_W["low_debt"]*d + QUALITY_W["earnings_positive"]*e
            for q, d, e in zip(roe_p, low_debt, earn_pos)]


def value(rows):
    # sector-relative multiples; cheaper (lower) is better -> invert the rank
    cheap = lambda f: [1 - p for p in percentile_rank(sector_relative(rows, f))]
    pe, pb, ps = cheap("pe"), cheap("pb"), cheap("ps")
    dy = percentile_rank([r["div_yield"] for r in rows])          # higher yield better
    return [VALUE_W["cheap_pe"]*a + VALUE_W["cheap_pb"]*b + VALUE_W["cheap_ps"]*c + VALUE_W["div_yield"]*d
            for a, b, c, d in zip(pe, pb, ps, dy)]


def momentum(rows):
    # 12-month return EXCLUDING the most recent month (standard 12-minus-1)
    mom = [((1 + r["ret_12m"]/100) / (1 + r["ret_1m"]/100) - 1) for r in rows]
    mom_p = percentile_rank(mom)
    reversal = [1 - p for p in percentile_rank([r["ret_1m"] for r in rows])]  # small contrarian nudge
    return [MOMENTUM_W["mom_12_1"]*m + MOMENTUM_W["reversal"]*rv for m, rv in zip(mom_p, reversal)]


def growth(rows):
    yoy = percentile_rank([r["eps_yoy"] for r in rows])
    qoq = percentile_rank([r["eps_qoq"] for r in rows])
    return [GROWTH_W["eps_yoy"]*a + GROWTH_W["eps_qoq"]*b for a, b in zip(yoy, qoq)]


# -----------------------------------------------------------------------------
# 3. COMPOSITE + DIVERSIFIED SELECTION
# -----------------------------------------------------------------------------
def score_and_select(rows):
    Q, V, M, G = quality(rows), value(rows), momentum(rows), growth(rows)
    for i, r in enumerate(rows):
        r["Q"], r["V"], r["M"], r["G"] = Q[i], V[i], M[i], G[i]
        r["composite"] = (WEIGHTS["quality"]*Q[i] + WEIGHTS["value"]*V[i]
                          + WEIGHTS["momentum"]*M[i] + WEIGHTS["growth"]*G[i])
        # eligibility gate
        r["eligible"] = (r["mcap_cr"] >= RULES["min_mcap_cr"] and r["roe"] > 0 and r["eps_latest"] > 0)

    ranked = sorted([r for r in rows if r["eligible"]], key=lambda r: r["composite"], reverse=True)

    picks, per_ind, per_macro = [], {}, {}
    for r in ranked:
        if per_ind.get(r["industry"], 0) >= RULES["max_per_industry"]:  continue
        if per_macro.get(r["macro"], 0) >= RULES["max_per_macro"]:      continue
        picks.append(r)
        per_ind[r["industry"]]  = per_ind.get(r["industry"], 0) + 1
        per_macro[r["macro"]]   = per_macro.get(r["macro"], 0) + 1
        if len(picks) >= RULES["n_stocks"]:
            break
    return picks


# -----------------------------------------------------------------------------
# 4. DUMMY DATA  (replace with your own rows — same fields — to reproduce)
# -----------------------------------------------------------------------------
STOCKS = [
    # code, industry, macro, roe%, D/E, PE, PB, PS, div_yield%, ret_12m%, ret_1m%, eps_yoy%, eps_qoq%, eps_latest, mcap_cr, is_financial
    dict(code="AAA", industry="Metals",  macro="Commodities", roe=22, de=0.4, pe=9,  pb=1.5, ps=1.2, div_yield=3.0, ret_12m=70, ret_1m=4, eps_yoy=40, eps_qoq=10, eps_latest=25, mcap_cr=45000, is_financial=False),
    dict(code="BBB", industry="Pharma",  macro="Healthcare",  roe=19, de=0.2, pe=24, pb=4.0, ps=3.5, div_yield=0.8, ret_12m=35, ret_1m=2, eps_yoy=22, eps_qoq=8,  eps_latest=40, mcap_cr=60000, is_financial=False),
    dict(code="CCC", industry="Bank",    macro="Financials",  roe=16, de=8.0, pe=8,  pb=1.1, ps=2.0, div_yield=1.5, ret_12m=25, ret_1m=1, eps_yoy=18, eps_qoq=5,  eps_latest=30, mcap_cr=90000, is_financial=True),
    dict(code="DDD", industry="IT",      macro="Technology",  roe=30, de=0.1, pe=28, pb=8.0, ps=6.0, div_yield=2.5, ret_12m=15, ret_1m=-1,eps_yoy=12, eps_qoq=3,  eps_latest=55, mcap_cr=120000,is_financial=False),
    dict(code="EEE", industry="Metals",  macro="Commodities", roe=14, de=0.9, pe=11, pb=1.8, ps=1.0, div_yield=2.0, ret_12m=55, ret_1m=6, eps_yoy=30, eps_qoq=15, eps_latest=18, mcap_cr=30000, is_financial=False),
    dict(code="FFF", industry="FMCG",    macro="Cons Staples",roe=45, de=0.0, pe=55, pb=15,  ps=8.0, div_yield=1.2, ret_12m=8,  ret_1m=0, eps_yoy=9,  eps_qoq=2,  eps_latest=70, mcap_cr=200000,is_financial=False),
    dict(code="GGG", industry="Power",   macro="Utilities",   roe=12, de=1.2, pe=13, pb=1.6, ps=1.5, div_yield=3.5, ret_12m=40, ret_1m=3, eps_yoy=15, eps_qoq=4,  eps_latest=12, mcap_cr=35000, is_financial=False),
    dict(code="HHH", industry="Auto",    macro="Cons Cyclical",roe=24,de=0.3, pe=22, pb=5.0, ps=2.8, div_yield=1.0, ret_12m=45, ret_1m=5, eps_yoy=28, eps_qoq=12, eps_latest=48, mcap_cr=80000, is_financial=False),
    dict(code="III", industry="Bank",    macro="Financials",  roe=9,  de=9.0, pe=7,  pb=0.8, ps=1.5, div_yield=0.5, ret_12m=10, ret_1m=-2,eps_yoy=5,  eps_qoq=1,  eps_latest=8,  mcap_cr=15000, is_financial=True),
    dict(code="JJJ", industry="Chemicals",macro="Commodities",roe=6,  de=1.5, pe=40, pb=3.0, ps=2.5, div_yield=0.3, ret_12m=-5, ret_1m=-3,eps_yoy=-10,eps_qoq=-4, eps_latest=5,  mcap_cr=8000,  is_financial=False),
]

if __name__ == "__main__":
    picks = score_and_select(STOCKS)
    print(f"{'rank':<5}{'code':<6}{'sector':<14}{'Q':>5}{'V':>5}{'M':>5}{'G':>5}{'score':>7}")
    for i, r in enumerate(picks, 1):
        print(f"{i:<5}{r['code']:<6}{r['macro']:<14}"
              f"{r['Q']:>5.2f}{r['V']:>5.2f}{r['M']:>5.2f}{r['G']:>5.2f}{r['composite']:>7.3f}")
    print("\nWeights:", WEIGHTS, "| Rules:", RULES)
