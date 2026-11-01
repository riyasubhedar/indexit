"""Independent check of the key figures (D-026) against the SEC's structured data (XBRL company facts).

The figures are read from the PDFs by rules; XBRL is what each company tagged in the same 10-K. A figure
passes if any usual tag for it has the same value for the same period. Debt has no single standard tag,
so its XBRL components are printed for review instead. Development check only: IndexIt doesn't use XBRL.

  uv run python spikes/check_figures_xbrl.py
"""

import json
from datetime import date

from indexit.figures import key_figures
from indexit.sec import _get

TICKERS = {"Advanced Micro Devices": "AMD", "Alphabet": "GOOGL", "Amazon.com": "AMZN", "Apple": "AAPL",
           "Expedia Group": "EXPE", "JPMorgan Chase": "JPM", "Microsoft": "MSFT", "NVIDIA": "NVDA",
           "Tesla": "TSLA", "Walmart": "WMT"}
TAGS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet",
                "RevenuesNetOfInterestExpense"],
    "cost_of_revenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"],
    "gross_profit": ["GrossProfit"],
    "rd": ["ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "total_assets": ["Assets"],
}
DEBT_TAGS = ["LongTermDebt", "LongTermDebtNoncurrent", "LongTermDebtCurrent", "ShortTermBorrowings",
             "CommercialPaper", "DebtCurrent", "LongTermDebtAndCapitalLeaseObligations",
             "LongTermDebtAndCapitalLeaseObligationsCurrent", "OtherLongTermDebtNoncurrent"]


def facts(ticker: str) -> dict:
    companies = json.loads(_get("https://www.sec.gov/files/company_tickers.json")).values()
    cik = next(int(c["cik_str"]) for c in companies if c["ticker"] == ticker)
    return json.loads(_get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"))["facts"].get("us-gaap", {})


def values(us_gaap: dict, tag: str, end: str, flow: bool) -> set[float]:
    """Values (US$ millions) tagged for a period ending within a week of `end` (a full year for flows)."""
    found = set()
    target = date.fromisoformat(end)
    for fact in us_gaap.get(tag, {}).get("units", {}).get("USD", []):
        if abs((date.fromisoformat(fact["end"]) - target).days) > 7:
            continue
        if flow and (not fact.get("start") or not 350 <= (date.fromisoformat(fact["end"]) - date.fromisoformat(fact["start"])).days <= 380):
            continue
        found.add(round(fact["val"] / 1e6, 1))
    return found


def main():
    figures = key_figures()
    passed = failed = untagged = 0
    for company, ticker in TICKERS.items():
        us_gaap = facts(ticker)
        for (name, year, metric), (figure, _) in sorted(figures.items()):
            if name != company:
                continue
            if metric == "debt":
                parts = {t: sorted(values(us_gaap, t, figure.period_end, False)) for t in DEBT_TAGS}
                parts = {t: v for t, v in parts.items() if v}
                print(f"  review  {company} FY{year} debt {figure.value:,.0f} ({figure.label}) | XBRL: {parts}")
                continue
            flow = metric not in ("cash", "total_assets")
            tagged = set().union(*(values(us_gaap, t, figure.period_end, flow) for t in TAGS[metric]))
            if not tagged:
                untagged += 1
                print(f"  no tag  {company} FY{year} {metric} {figure.value:,.0f}")
            elif any(abs(v - figure.value) <= 1 for v in tagged):
                passed += 1
            else:
                failed += 1
                print(f"  DIFF    {company} FY{year} {metric}: PDF {figure.value:,.0f} ({figure.label!r}, p.{figure.page}) "
                      f"vs XBRL {sorted(tagged)}")
    print(f"\nmatched {passed} · different {failed} · no XBRL value to compare {untagged}")


if __name__ == "__main__":
    main()
