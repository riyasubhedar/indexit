"""Key figures (D-026): standard income-statement and balance-sheet figures for every filing, read by
rules from the cached Docling tables (D-022), so questions across many companies take one lookup instead
of one search per company, and margins and rankings are worked out by code, not by the model.

Nothing is guessed. A figure is kept only if its row label is a recognised name for it, its table is the
consolidated statement itself, its column's period and units can be read, and it passes the checks below.
Anything else is left out, and the agent falls back to search.
"""

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import pymupdf

from indexit.documents import FILINGS_DIR, Filing, list_filings
from indexit.tables import Table, _cache_path

# Row labels, most specific first: the first match in this order wins (AMD has both "Cost of sales" and
# "Total cost of sales"; the total is the one that adds up to gross profit).
INCOME_ROWS = {
    "revenue": ["total revenues", "total revenue", "total net revenues", "total net revenue", "revenues",
                "revenue", "net revenues", "net revenue", "total net sales", "net sales"],
    "cost_of_revenue": ["total cost of revenues", "total cost of revenue", "total cost of sales", "cost of revenues",
                        "cost of revenue", "cost of sales", "cost of goods sold"],
    "gross_profit": ["total gross margin", "gross profit", "gross margin"],
    "rd": ["research and development", "research and development expense", "research and development expenses",
           "total research and development"],
    "operating_income": ["operating income", "operating income (loss)", "income from operations",
                         "income (loss) from operations", "operating profit"],
}
# Net income: the company's own share (Tesla, Walmart and Expedia also report a total that includes
# minority owners). "Applicable to common stockholders" (after preferred dividends) is not the headline.
NET_INCOME_ATTRIBUTABLE = re.compile(r"^(consolidated )?net (income|earnings) attributable to (?!noncontrolling)")
NET_INCOME_ROWS = ["net income", "net income (loss)", "net earnings"]

BALANCE_ROWS = {
    "cash": ["cash and cash equivalents"],
    "total_assets": ["total assets"],
}
# Debt = every debt line on the face of the balance sheet, summed (Apple lists term debt twice: current
# and non-current). Lease lines count only when the company files them as debt (Tesla's "debt and
# finance leases"). Some companies fold the current portion into other liabilities; the tool says so.
DEBT_ROW = re.compile(
    r"^(short-term debt|short-term borrowings|commercial paper|term debt|notes payable|"
    r"(current portion of |current maturities of )?long-term debt|long-term debt due within one year|"
    r"current portion of debt and finance leases|debt and finance leases)\b"
)
NOT_DEBT = re.compile(r"lease (obligation|liabilit)|operating lease")

INCOME_TITLE = re.compile(r"statements? of (operations|income|earnings)|^income statements?\b", re.I)
BALANCE_TITLE = re.compile(r"balance sheets?|statements? of financial (position|condition)", re.I)
UNITS = re.compile(r"\bin[\s.]+(thousands|millions|billions)", re.I)  # also "(In.millions" (Expedia)
TO_MILLIONS = {"thousands": 0.001, "millions": 1.0, "billions": 1000.0}
_MONTH = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?"
FULL_DATE = re.compile(_MONTH + r"\s+(\d{1,2}),?\s*[-.]?\s*(\d{4})")
MONTH_DAY = re.compile(_MONTH + r"\s+(\d{1,2})\b")
YEAR = re.compile(r"\b(19|20)\d{2}\b")


@dataclass(frozen=True)
class Figure:
    company: str
    fiscal_year: int
    period_end: str  # e.g. "2025-12-27"
    metric: str
    value: float  # US$ millions
    label: str  # the row as printed, e.g. "Total net sales" (for debt: the lines summed)
    file: str
    page: int
    source_fiscal_year: int  # the filing it came from (a 10-K shows two or three years)


def _norm(label: str) -> str:
    """"Total assets (a)" / "Net sales:" / "TOTAL ASSETS" -> "total assets". Bracketed notes go too:
    Expedia's "Cost of revenue (exclusive of depreciation…)" is its cost of revenue."""
    label = re.sub(r"\([^)]*\)", "", label.lower())
    return re.sub(r"\s+", " ", label).strip(" :,.")


def _number(cell: str) -> float | None:
    """"$ 34,639" -> 34639; "(131)" -> -131; "-" / "—" / "" -> None (no figure, never zero)."""
    text = cell.replace("$", "").replace(",", "").replace("—", "").replace("–", "").strip()
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("() ")
    if not re.fullmatch(r"\d+(\.\d+)?", text):
        return None
    return -float(text) if negative else float(text)


def _cells(markdown: str) -> list[list[str]]:
    """Markdown table rows as cell lists, without the header and separator lines."""
    lines = [line for line in markdown.splitlines() if line.strip().startswith("|")]
    return [[c.strip() for c in line.strip().strip("|").split("|")] for line in lines[2:]]


def _units(table: Table, page_text: str) -> float | None:
    for text in [table.title, *table.columns, page_text]:
        match = UNITS.search(text or "")
        if match:
            return TO_MILLIONS[match.group(1).lower()]
    return None


def _column_end(header: str, context: str, filing: Filing) -> date | None:
    """A column's period end from its header ("December 27, 2025"), or its year plus the month and day
    printed elsewhere in the table ("June 30," above Microsoft's "2025"), or the filing's own year end."""
    full = FULL_DATE.search(header)
    if full:
        return datetime.strptime(f"{full.group(1)[:3]} {full.group(2)} {full.group(3)}", "%b %d %Y").date()
    year = YEAR.search(header)
    if not year:
        return None
    month_day = MONTH_DAY.search(context)
    if month_day:
        return datetime.strptime(f"{month_day.group(1)[:3]} {month_day.group(2)} {year.group(0)}", "%b %d %Y").date()
    own = date.fromisoformat(filing.period_end)
    return own.replace(year=int(year.group(0)))


def _fiscal_year(end: date, filing: Filing) -> int:
    """Label a column the way the filing labels its own year (NVIDIA's year ending Jan 2026 is FY2026)."""
    own = date.fromisoformat(filing.period_end)
    return filing.fiscal_year - round((own - end).days / 365.25)


def _statement(tables: list[Table], title: re.Pattern, must_have: str) -> Table | None:
    """The consolidated statement itself (not an MD&A summary or segment table): the longest table whose
    title starts by naming the statement (not a long caption that mentions it, like JPMorgan's average
    balances table) and that has the given row."""
    found = [t for t in tables if (m := title.search(t.title)) and m.start() <= 50 and "cash flow" not in t.title.lower()
             and any(_norm(r).startswith(must_have) for r in t.rows)]
    return max(found, key=lambda t: len(t.rows), default=None)


def _read(table: Table, filing: Filing, pdf: pymupdf.Document) -> tuple[list[tuple[date, int]], list[tuple[str, list[float | None]]]] | None:
    """(column periods, [(row label, values per column)]), or None if periods or units can't be read."""
    page_text = pdf[table.page - 1].get_text() if 0 < table.page <= len(pdf) else ""
    scale = _units(table, page_text)
    if scale is None:
        return None
    context = " ".join([table.title, table.columns[0] if table.columns else ""])
    periods = []
    for header in table.columns[1:]:
        end = _column_end(header, context + " " + page_text[:400], filing)
        if end is None:
            return None
        periods.append((end, len(periods) + 1))
    if len({end for end, _ in periods}) != len(periods):
        return None  # two columns for one period: not a plain statement layout
    rows = []
    for cells in _cells(table.markdown):
        if len(cells) != len(table.columns):
            return None  # merged or split cells: the values can't be matched to their years
        values = [_number(c) for c in cells[1:]]
        rows.append((cells[0], [v * scale if v is not None else None for v in values]))
    return periods, rows


def _income_figures(table: Table, filing: Filing, pdf) -> list[Figure]:
    read = _read(table, filing, pdf)
    if not read:
        return []
    periods, rows = read
    by_label: dict[str, tuple[str, list]] = {}
    for label, values in rows:
        by_label.setdefault(_norm(label), (label, values))
    picked: dict[str, tuple[str, list]] = {}
    for metric, names in INCOME_ROWS.items():
        for name in names:
            if name in by_label and any(v is not None for v in by_label[name][1]):
                picked[metric] = by_label[name]
                break
    attributable = [(label, values) for label, values in rows if NET_INCOME_ATTRIBUTABLE.match(_norm(label))]
    if attributable:
        picked["net_income"] = attributable[0]
    else:
        for name in NET_INCOME_ROWS:
            if name in by_label:
                picked["net_income"] = by_label[name]
                break
    return _per_period(picked, periods, filing, table.page)


def _balance_figures(table: Table, filing: Filing, pdf) -> list[Figure]:
    read = _read(table, filing, pdf)
    if not read:
        return []
    periods, rows = read
    picked: dict[str, tuple[str, list]] = {}
    for metric, names in BALANCE_ROWS.items():
        for label, values in rows:
            if _norm(label) in names:
                picked.setdefault(metric, (label, values))
    labels = [_norm(label) for label, _ in rows]
    if "deposits" not in labels:  # a bank's deposits and borrowings are its raw material, not comparable debt
        lines = [(label, values) for label, values in rows
                 if DEBT_ROW.match(_norm(label)) and not NOT_DEBT.search(_norm(label))]
        if lines:
            total = [sum(v for v in col if v is not None) if any(v is not None for v in col) else None
                     for col in zip(*[values for _, values in lines])]
            picked["debt"] = (" + ".join(label for label, _ in lines), total)
    return _per_period(picked, periods, filing, table.page)


def _per_period(picked: dict, periods: list, filing: Filing, page: int) -> list[Figure]:
    figures = []
    for metric, (label, values) in picked.items():
        for (end, column), value in zip(periods, values):
            if value is None:
                continue
            figures.append(Figure(filing.company, _fiscal_year(end, filing), end.isoformat(), metric,
                                  value, re.sub(r"\s+", " ", label).strip(" :"), filing.file, page, filing.fiscal_year))
    return figures


def _passes_checks(figures: list[Figure]) -> list[Figure]:
    """Drop a year's figures that don't add up, rather than show a wrong number."""
    by_year: dict[int, dict[str, Figure]] = {}
    for f in figures:
        by_year.setdefault(f.fiscal_year, {})[f.metric] = f
    keep = []
    for year, m in by_year.items():
        value = {k: f.value for k, f in m.items()}
        bad = set()
        revenue = value.get("revenue")
        if revenue is not None and revenue <= 0:
            bad |= {"revenue", "cost_of_revenue", "gross_profit", "rd", "operating_income", "net_income"}
        if revenue:
            for k in ("operating_income", "net_income", "rd", "cost_of_revenue", "gross_profit"):
                if k in value and abs(value[k]) > revenue:
                    bad.add(k)
            if {"cost_of_revenue", "gross_profit"} <= value.keys():
                if abs(revenue - value["cost_of_revenue"] - value["gross_profit"]) > max(2, 0.002 * revenue):
                    bad |= {"cost_of_revenue", "gross_profit"}  # they don't add up: keep neither
        assets = value.get("total_assets")
        if assets:
            for k in ("cash", "debt"):
                if k in value and not 0 <= value[k] <= assets:
                    bad.add(k)
        keep += [f for k, f in m.items() if k not in bad]
    return keep


@lru_cache(maxsize=512)
def _filing_figures(path: Path, cache_mtime: float) -> tuple[tuple[Figure, ...], bool]:
    """(figures, whether the balance sheet is a bank's: it has a "Deposits" liability)."""
    filing = next((f for f in list_filings(path.parent) if f.file == path.name), None)
    cache = _cache_path(path)
    if filing is None or not cache.exists():
        return (), False
    tables = [Table(**t) for t in json.loads(cache.read_text())]
    figures = []
    with pymupdf.open(path) as pdf:
        income = _statement(tables, INCOME_TITLE, "net ")
        if income:
            figures += _income_figures(income, filing, pdf)
        balance = _statement(tables, BALANCE_TITLE, "total assets")
        if balance:
            figures += _balance_figures(balance, filing, pdf)
    bank = bool(balance) and any(_norm(r) == "deposits" for r in balance.rows)
    return tuple(_passes_checks(figures)), bank


def filing_figures(filing: Filing, folder: Path = FILINGS_DIR) -> list[Figure]:
    """Figures from one filing ([] until its tables have been extracted)."""
    path = folder / filing.file
    cache = _cache_path(path)
    return list(_filing_figures(path, cache.stat().st_mtime if cache.exists() else 0.0)[0])


def banks(folder: Path = FILINGS_DIR) -> set[str]:
    """Companies whose balance sheet is a bank's. Their debt, cash and costs aren't comparable."""
    found = set()
    for filing in list_filings(folder):
        cache = _cache_path(folder / filing.file)
        if cache.exists() and _filing_figures(folder / filing.file, cache.stat().st_mtime)[1]:
            found.add(filing.company)
    return found


def key_figures(folder: Path = FILINGS_DIR) -> dict[tuple[str, int, str], tuple[Figure, list[Figure]]]:
    """(company, fiscal year, metric) -> (figure from the most recent filing (D-011), older filings'
    figures for the same year that differ, i.e. restatements)."""
    every: dict[tuple[str, int, str], list[Figure]] = {}
    for filing in list_filings(folder):
        for f in filing_figures(filing, folder):
            every.setdefault((f.company, f.fiscal_year, f.metric), []).append(f)
    result = {}
    for key, figures in every.items():
        figures.sort(key=lambda f: f.source_fiscal_year, reverse=True)
        latest = figures[0]
        restated = [f for f in figures[1:] if abs(f.value - latest.value) > max(1, 0.002 * abs(latest.value))]
        result[key] = (latest, restated)
    return result


def pending_filings(folder: Path = FILINGS_DIR) -> list[Filing]:
    """Filings whose tables are still being extracted, so they have no figures yet."""
    return [f for f in list_filings(folder) if not _cache_path(folder / f.file).exists()]


# What compare_companies and the app's Compare view offer. Ratios and growth are calculated here, from the
# statement lines, so the model never does the arithmetic.
METRICS = {
    "revenue": "Revenue", "cost_of_revenue": "Cost of revenue", "gross_profit": "Gross profit",
    "rd": "Research and development (R&D)", "operating_income": "Operating income", "net_income": "Net income",
    "cash": "Cash and cash equivalents", "total_assets": "Total assets", "debt": "Debt on the balance sheet",
}
RATIOS = {  # name: (label, numerator, denominator)
    "gross_margin": ("Gross margin (gross profit ÷ revenue)", "gross_profit", "revenue"),
    "operating_margin": ("Operating margin (operating income ÷ revenue)", "operating_income", "revenue"),
    "net_margin": ("Net margin (net income ÷ revenue)", "net_income", "revenue"),
    "rd_to_revenue": ("R&D as a share of revenue", "rd", "revenue"),
}
GROWTH = {"revenue_growth": ("Revenue growth vs the year before", "revenue"),
          "net_income_growth": ("Net income growth vs the year before", "net_income")}
NOT_COMPARABLE_FOR_BANKS = {"cost_of_revenue", "gross_profit", "rd", "operating_income", "cash", "debt",
                            "total_assets", "gross_margin", "operating_margin", "rd_to_revenue"}
# Plain-English meanings, shown under the Compare view's title (definitions, not judgements).
MEANINGS = {
    "gross_margin": "The share of revenue left after the direct cost of what was sold.",
    "operating_margin": "The share of revenue left after running the business, before interest and taxes.",
    "net_margin": "The share of revenue left as profit after every cost and tax.",
    "rd_to_revenue": "How much of each dollar of revenue goes to research and development.",
    "revenue_growth": "How much revenue changed from the year before.",
    "net_income_growth": "How much net income changed from the year before.",
    "cash": "Cash in the bank plus investments that can be turned into cash within about three months.",
    "debt": "Money borrowed that must be repaid: borrowings, commercial paper and notes on the balance sheet.",
}


def label_for(metric: str) -> str:
    return METRICS.get(metric) or (RATIOS.get(metric) or GROWTH[metric])[0]


def _source(f: Figure) -> dict:
    return {"document": f"{f.company} FY{f.source_fiscal_year} 10-K", "file": f.file, "page": f.page, "line": f.label}


def comparison(metric: str, fiscal_year: int | None = None, companies: list[str] | None = None,
               folder: Path = FILINGS_DIR) -> dict:
    """One figure across companies, ranked highest first: {metric, label, unit, basis, rows, missing,
    notes, years}. Each row has its value, the text to show, its fiscal year and period end, and its sources."""
    from indexit.documents import resolve_company

    if metric not in METRICS and metric not in RATIOS and metric not in GROWTH:
        raise ValueError(f"Unknown metric {metric!r}. Choose one of: {', '.join([*METRICS, *RATIOS, *GROWTH])}.")
    figures = key_figures(folder)
    notes, wanted = [], sorted({f.company for f in list_filings(folder)})
    if companies:
        wanted = []
        for name in companies:
            found = resolve_company(name, folder)
            if found:
                wanted.append(found)
            else:
                notes.append(f"No filings for {name!r} in the library.")
    bank_names = banks(folder)
    base = RATIOS[metric][1:] if metric in RATIOS else (GROWTH[metric][1],) if metric in GROWTH else (metric,)
    rows, missing = [], []
    for company in wanted:
        years = sorted({y for c, y, _ in figures if c == company}, reverse=True)  # years with any figure
        year = fiscal_year if fiscal_year else (years[0] if years else None)
        if company in bank_names and metric in NOT_COMPARABLE_FOR_BANKS:
            missing.append({"company": company, "reason": "A bank: its costs and balance sheet work differently "
                            "(deposits and loans are its raw material), so this figure isn't comparable."})
            continue
        got = {m: figures.get((company, year, m), (None, []))[0] for m in base}
        if metric in GROWTH:
            got["prior"] = figures.get((company, (year or 0) - 1, base[0]), (None, []))[0]
        if any(v is None for v in got.values()):
            if any(f.company == company for f in pending_filings(folder)):
                reason = "Its tables are still being extracted."
            elif year is None or year not in years:
                reason = (f"No FY{year} figures (fiscal years with figures: "
                          f"{', '.join(str(y) for y in sorted(years)) or 'none'}).")
            else:
                lines = [METRICS[m] for m, v in got.items() if v is None and m != "prior"]
                reason = (f"No line for {', '.join(lines) or 'the year before'} on its statement "
                          "(it may report it under another name).")
            missing.append({"company": company, "reason": reason})
            continue
        main = got[base[0]]
        if metric in RATIOS:
            value = got[base[0]].value / got[base[1]].value * 100
            shown = f"{value:.1f}%"
            inputs = f"${got[base[0]].value:,.0f}M ÷ ${got[base[1]].value:,.0f}M"  # units shown: no guessing
            sources = list({id(f): _source(f) for f in got.values()}.values())
        elif metric in GROWTH:
            prior = got["prior"]
            value = (main.value - prior.value) / abs(prior.value) * 100
            shown = f"{value:+.1f}%"
            inputs = f"${prior.value:,.0f}M → ${main.value:,.0f}M"
            sources = [_source(main)] + ([_source(prior)] if (prior.file, prior.page) != (main.file, main.page) else [])
        else:
            value = main.value
            shown = f"{'−' if value < 0 else ''}${abs(value):,.0f}M"
            inputs = ""
            sources = [_source(main)]
            restated = figures[(company, year, metric)][1]
            if restated:
                notes.append(f"{company} FY{year}: a newer filing restated this figure (older: "
                             + ", ".join(f"${f.value:,.0f}M in the FY{f.source_fiscal_year} 10-K" for f in restated) + ").")
            if metric == "debt" and not re.search(r"current|short-term|commercial paper|within one year", main.label, re.I):
                notes.append(f"{company}: its balance sheet shows long-term debt only; the part due within a "
                             "year is inside other liabilities, so its total debt is somewhat higher.")
            if metric == "debt" and "lease" in main.label.lower():
                notes.append(f"{company}: its debt lines include finance leases.")
        rows.append({"company": company, "value": value, "shown": shown, "inputs": inputs,
                     "fiscal_year": main.fiscal_year, "period_end": main.period_end, "sources": sources})
    rows.sort(key=lambda r: r["value"], reverse=True)
    if len({r["period_end"][5:] for r in rows}) > 1:
        notes.append("Fiscal years end on different dates: each row shows its own period.")
    if metric == "cash":
        notes.append("Cash and cash equivalents only. Many companies hold more in short-term investments "
                     "(marketable securities), on separate balance-sheet lines not counted here.")
    if metric == "debt":
        notes.append("Debt = the debt lines on the face of each balance sheet (borrowings, commercial paper, "
                     "notes), excluding operating leases.")
    return {
        "metric": metric, "label": label_for(metric), "meaning": MEANINGS.get(metric, ""),
        "unit": "%" if metric in RATIOS or metric in GROWTH else "US$ millions",
        "basis": f"fiscal year {fiscal_year}" if fiscal_year else "each company's latest fiscal year",
        "rows": rows, "missing": missing, "notes": notes,
        "years": sorted({y for _, y, m in figures if m in base}, reverse=True),
    }


def compare(metric: str, fiscal_year: int | None = None, companies: list[str] | None = None,
            folder: Path = FILINGS_DIR) -> str:
    """The comparison as text for the agent: a ranked markdown table with periods and source pages."""
    try:
        c = comparison(metric, fiscal_year, companies, folder)
    except ValueError as error:
        return str(error)
    unit = "" if c["unit"] == "%" else f" ({c['unit']})"
    lines = [f"{c['label']}{unit}, {c['basis']}. Ranked highest first; figures from each company's own statements.",
             "| Rank | Company | Fiscal year | Period end | Value | Source |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(c["rows"], 1):
        value = f"{r['shown']} ({r['inputs']})" if r["inputs"] else f"{r['value']:,.0f}"
        sources = "; ".join(f'{s["document"]}, p.{s["page"]} ("{s["line"]}")' for s in r["sources"])
        lines.append(f"| {i} | {r['company']} | FY{r['fiscal_year']} | {r['period_end']} | {value} | {sources} |")
    parts = ["\n".join(lines)]
    if c["missing"]:
        parts.append("Not in this table:\n" + "\n".join(f"- {m['company']}: {m['reason']} Use search_filings."
                                                        if "bank" not in m["reason"] else f"- {m['company']}: {m['reason']}"
                                                        for m in c["missing"]))
    if c["notes"]:
        parts.append("Notes:\n" + "\n".join(f"- {n}" for n in c["notes"]))
    return "\n\n".join(parts)


def _short(company: str) -> str:
    return company.replace(".com", "").replace("Advanced Micro Devices", "AMD")


SHORT_NAMES = {"rd": "R&D spending", "rd_to_revenue": "R&D as a share of revenue", "cash": "cash",
               "debt": "debt", "revenue_growth": "revenue growth", "net_income_growth": "net income growth"}


def short_name(metric: str) -> str:
    """"net_margin" -> "net margin": the label without its explanation, for use inside a sentence."""
    if metric in SHORT_NAMES:
        return SHORT_NAMES[metric]
    label = label_for(metric).split(" (")[0]
    return label[0].lower() + label[1:]


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def insights(c: dict, folder: Path = FILINGS_DIR) -> list[dict]:
    """2–4 plain sentences about a comparison, written by rules from its rows, so they can't say anything
    the table doesn't: who leads and trails, anything below zero, and companies whose ranks diverge. Each
    comes with a question the reader can hand to IndexIt for the reasons behind it. No judgements."""
    rows, metric = c["rows"], c["metric"]
    if not rows:
        return []
    what = short_name(metric)
    fy = lambda r: f"FY{r['fiscal_year']}"
    out = [{"text": f"{rows[0]['company']} has the highest {what}: {rows[0]['shown']} ({fy(rows[0])}).",
            "ask": f"What drives {_short(rows[0]['company'])}'s {what}?"}]
    if len(rows) >= 3 and rows[-1]["value"] >= 0:
        low = rows[-1]
        out.append({"text": f"{low['company']} has the lowest: {low['shown']} ({fy(low)}).",
                    "ask": f"Why is {_short(low['company'])}'s {what} lower than the others'?"})
    for r in [r for r in rows if r["value"] < 0][:1]:
        if metric in GROWTH:
            base = what.replace(" growth", "")
            out.append({"text": f"{r['company']}'s {base} fell {r['shown'].lstrip('-−')} ({fy(r)}).",
                        "ask": f"Why did {_short(r['company'])}'s {base} fall in {fy(r)}?"})
        else:
            out.append({"text": f"{r['company']}'s {what} was below zero: {r['shown']} ({fy(r)}).",
                        "ask": f"Why was {_short(r['company'])}'s {what} below zero in {fy(r)}?"})
    # Rank divergence: margins and profit against revenue; R&D in dollars against R&D as a share of revenue.
    pair = {"gross_margin": "revenue", "operating_margin": "revenue", "net_margin": "revenue", "net_income": "revenue",
            "rd": "rd_to_revenue", "rd_to_revenue": "rd"}.get(metric)
    if pair and len(rows) >= 4:
        year = None if c["basis"].startswith("each") else int(c["basis"].split()[-1])
        other = comparison(pair, year, [r["company"] for r in rows], folder)
        here = {r["company"]: i for i, r in enumerate(rows)}
        there = {r["company"]: i for i, r in enumerate(other["rows"])}
        common = [k for k in here if k in there]
        if common:
            co = max(common, key=lambda k: abs(here[k] - there[k]))
            if abs(here[co] - there[co]) >= max(2, len(common) // 2):
                n = len(common)
                out.append({"text": f"{co} ranks {_ordinal(there[co] + 1)} of {n} on {short_name(pair)} "
                                    f"({other['rows'][there[co]]['shown']}) but {_ordinal(here[co] + 1)} on {what} "
                                    f"({rows[here[co]]['shown']}).",
                            "ask": f"Why does {_short(co)} rank {_ordinal(there[co] + 1)} on {short_name(pair)} but "
                                   f"{_ordinal(here[co] + 1)} on {what}?"})
    return out[:4]


# Side by side (D-026): two companies on every figure, built from comparison() so the same checks, bank
# rules and notes apply. Sections group the figures the way a reader thinks about a company.
PAIR_SECTIONS = [
    ("Size and growth", ["revenue", "revenue_growth", "net_income_growth"]),
    ("Profitability", ["gross_profit", "gross_margin", "operating_income", "operating_margin", "net_income", "net_margin"]),
    ("Investment", ["rd", "rd_to_revenue"]),
    ("Balance sheet", ["cash", "debt", "total_assets"]),
]
PERCENT = set(RATIOS) | set(GROWTH)


def _gap(metric: str, a: dict | None, b: dict | None) -> str:
    """"6.2×" for amounts (both above zero), "+43.1 pts" for percentages (first minus second)."""
    if not a or not b:
        return ""
    if metric in PERCENT:
        return f"{a['value'] - b['value']:+.1f} pts"
    if a["value"] > 0 and b["value"] > 0:
        big, small = max(a["value"], b["value"]), min(a["value"], b["value"])
        return f"{big / small:.1f}×"
    return ""


def _when(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%b} {d.day}, {d.year}"


def side_by_side(first: str, second: str, fiscal_year: int | None = None, folder: Path = FILINGS_DIR) -> dict:
    """{companies, periods, sections: [{title, rows: [{metric, name, cells: [cell|None, cell|None], gap}]}],
    missing: {company: [reasons]}, notes, insights}. A cell is a comparison() row."""
    from indexit.documents import resolve_company

    names = [resolve_company(first, folder), resolve_company(second, folder)]
    if None in names or names[0] == names[1]:
        raise ValueError("Choose two different companies from the library.")
    sections, notes, by_metric = [], [], {}
    no_line = {n: [] for n in names}  # lines a company's statements don't have
    other = {n: [] for n in names}  # any other reason (a bank, still extracting, no figures that year)
    for title, metrics in PAIR_SECTIONS:
        rows = []
        for metric in metrics:
            c = comparison(metric, fiscal_year, names, folder)
            cells = [next((r for r in c["rows"] if r["company"] == n), None) for n in names]
            for m in c["missing"]:
                line = re.match(r"No line for (.+?) on its statement", m["reason"])
                if line:
                    for item in line.group(1).split(", "):
                        if item not in no_line[m["company"]]:
                            no_line[m["company"]].append(item)
                else:
                    reason = m["reason"].replace("so this figure isn't comparable",
                                                 "so its costs, R&D, cash, debt and assets aren't comparable")
                    if reason not in other[m["company"]]:
                        other[m["company"]].append(reason)
            notes += [n for n in c["notes"] if n not in notes and not n.startswith("Fiscal years end")]
            by_metric[metric] = cells
            rows.append({"metric": metric, "name": label_for(metric).split(" (")[0], "cells": cells,
                         "gap": _gap(metric, *cells), "percent": metric in PERCENT})
        sections.append({"title": title, "rows": rows})
    missing = {}
    for n in names:
        reasons = list(other[n])
        if no_line[n]:
            reasons.append(f"No line on its statements for {', '.join(x if x.startswith('R&D') else x[0].lower() + x[1:] for x in no_line[n])} "
                           "(it may report them under other names).")
        if reasons:
            missing[n] = reasons
    periods = []
    for i, n in enumerate(names):
        cell = next((cells[i] for cells in by_metric.values() if cells[i]), None)
        periods.append({"company": n, "fiscal_year": cell["fiscal_year"], "period_end": cell["period_end"]} if cell else None)
    if all(periods):
        days = abs((date.fromisoformat(periods[0]["period_end"]) - date.fromisoformat(periods[1]["period_end"])).days)
        if days > 20:
            notes.insert(0, f"Their fiscal years end on different dates ({_short(names[0])}: "
                            f"{_when(periods[0]['period_end'])}; {_short(names[1])}: {_when(periods[1]['period_end'])}), "
                            "so the figures cover different 12-month periods.")
    return {"companies": names, "periods": periods, "sections": sections, "missing": missing, "notes": notes,
            "insights": _pair_insights(names, by_metric)}


def _pair_insights(names: list[str], by_metric: dict) -> list[dict]:
    """Rule-based sentences about two companies: relative size, growth in opposite directions, and the
    widest percentage gaps (3+ points). Each states both values; none judges which is better."""
    short = [_short(n) for n in names]
    pair = lambda metric: by_metric.get(metric, [None, None])
    out = []
    rev = pair("revenue")
    if all(rev) and rev[0]["value"] > 0 and rev[1]["value"] > 0:
        big = 0 if rev[0]["value"] >= rev[1]["value"] else 1
        times = rev[big]["value"] / rev[1 - big]["value"]
        if times >= 1.2:
            out.append({"text": f"{names[big]}'s revenue is {times:.1f} times {short[1 - big]}'s "
                                f"({rev[big]['shown']} vs {rev[1 - big]['shown']}).",
                        "ask": f"How do {short[0]}'s and {short[1]}'s businesses differ in what they sell?"})
    growth = pair("revenue_growth")
    opposite = all(growth) and (growth[0]["value"] >= 0) != (growth[1]["value"] >= 0)
    if opposite:
        up = 0 if growth[0]["value"] >= 0 else 1
        out.append({"text": f"{names[up]}'s revenue grew {growth[up]['shown'].lstrip('+')}; "
                            f"{short[1 - up]}'s fell {growth[1 - up]['shown'].lstrip('-−')}.",
                    "ask": f"Why did {short[1 - up]}'s revenue fall while {short[up]}'s grew?"})
    candidates = ["net_margin", "operating_margin", "gross_margin", "rd_to_revenue"] + ([] if opposite else ["revenue_growth"])
    gaps = sorted(((abs(pair(m)[0]["value"] - pair(m)[1]["value"]), m) for m in candidates if all(pair(m))), reverse=True)
    for gap, metric in gaps[:2]:
        if gap < 3:
            break
        cells = pair(metric)
        hi = 0 if cells[0]["value"] >= cells[1]["value"] else 1
        what = short_name(metric)
        out.append({"text": f"{names[hi]}'s {what} is {cells[hi]['shown']}; {short[1 - hi]}'s is {cells[1 - hi]['shown']}.",
                    "ask": f"Why is {short[hi]}'s {what} higher than {short[1 - hi]}'s?"})
    return out[:4]
