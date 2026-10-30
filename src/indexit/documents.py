"""Filing metadata read from each 10-K's cover page: company, fiscal year, period end."""

import json
import os
import re
from dataclasses import dataclass, replace
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import pymupdf

PROJECT_DIR = Path(__file__).resolve().parents[2]
FILINGS_DIR = Path(os.environ.get("INDEXIT_FOLDER", PROJECT_DIR / "data" / "filings"))
# The library (D-024): per file, what the app knows beyond the cover page (the name the user typed, the
# SEC ticker, corrections) and its indexing status. A folder without one is used as-is (every PDF).
LIBRARY_FILE = "library.json"
SEARCHABLE = {"searchable", "ready"}  # text indexed; tables may still be extracting

# "Commission file number: 0-23985", "Commission File No. 000-22513", or with a two-column cover
# interleaving other text: "Commission file December 31, 2024 number 1-5805" (JPMorgan).
_FILE_NO = r"(?i:commission file\b.{0,60}?\b(?:number|no\.?))\s*:?\s*\d[\d-]*[\s_]*"
# Usual layout: "Commission File Number 0-23985  NVIDIA CORPORATION (Exact name of registrant…".
_COMPANY = re.compile(_FILE_NO + r"(.+?)\s*\((?i:exact name of registrant)")
# Fallback (e.g. Microsoft): the name is the run of CAPITALISED words after the file number,
# ending before the state of incorporation, an ID number or a "(".
_STATES = (
    "ALABAMA|ALASKA|ARIZONA|ARKANSAS|CALIFORNIA|COLORADO|CONNECTICUT|DELAWARE|FLORIDA|GEORGIA|HAWAII|IDAHO|"
    "ILLINOIS|INDIANA|IOWA|KANSAS|KENTUCKY|LOUISIANA|MAINE|MARYLAND|MASSACHUSETTS|MICHIGAN|MINNESOTA|"
    "MISSISSIPPI|MISSOURI|MONTANA|NEBRASKA|NEVADA|NEW HAMPSHIRE|NEW JERSEY|NEW MEXICO|NEW YORK|NORTH CAROLINA|"
    "NORTH DAKOTA|OHIO|OKLAHOMA|OREGON|PENNSYLVANIA|RHODE ISLAND|SOUTH CAROLINA|SOUTH DAKOTA|TENNESSEE|TEXAS|"
    "UTAH|VERMONT|VIRGINIA|WASHINGTON|WEST VIRGINIA|WISCONSIN|WYOMING"
)
_COMPANY_CAPS = re.compile(
    _FILE_NO + r"((?:[A-Z][A-Z0-9.,&'-]*\s+)*?[A-Z][A-Z0-9.,&'-]*)(?=\s*\(|\s+(?:" + _STATES + r")\b|\s+\d)"
)
_KEEP_CAPS = {"NVIDIA", "AMD", "IBM", "AT&T"}  # brands written in capitals
_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
# The first date after "fiscal year ended", allowing interleaved text from two-column covers.
_PERIOD_END = re.compile(r"(?i:fiscal year ended)\b.{0,80}?((?:" + _MONTHS + r") \d{1,2}, \d{4})")


@dataclass(frozen=True)
class Filing:
    file: str
    company: str
    fiscal_year: int  # labelled by the year the fiscal year ends in (NVIDIA FY2026 ends Jan 2026)
    period_end: str  # e.g. "2026-01-25"
    pages: int

    @property
    def label(self) -> str:
        return f"{self.company} FY{self.fiscal_year} 10-K"


@lru_cache
def describe(path: Path) -> Filing:
    with pymupdf.open(path) as pdf:
        cover = " ".join(pdf[0].get_text().split())
        pages = len(pdf)
    company = _COMPANY.search(cover) or _COMPANY_CAPS.search(cover)
    period = _PERIOD_END.search(cover)
    end = datetime.strptime(period.group(1), "%B %d, %Y") if period else None
    return Filing(
        file=path.name,
        company=_short_name(company.group(1)) if company else path.stem,
        fiscal_year=end.year if end else 0,
        period_end=end.date().isoformat() if end else "unknown",
        pages=pages,
    )


def read_library(folder: Path = FILINGS_DIR) -> dict | None:
    path = folder / LIBRARY_FILE
    return json.loads(path.read_text()) if path.exists() else None


def write_library(library: dict, folder: Path = FILINGS_DIR) -> None:
    tmp = folder / f".{LIBRARY_FILE}.tmp"
    tmp.write_text(json.dumps(library, indent=1))
    tmp.replace(folder / LIBRARY_FILE)  # atomic: the search process never reads a half-written file


def list_filings(folder: Path = FILINGS_DIR) -> list[Filing]:
    """Searchable filings. With a library file, only its entries whose text is indexed, with the
    library's company / fiscal year where they differ from the cover page."""
    library = read_library(folder)
    filings = []
    for path in folder.glob("*.pdf"):
        if library is None:
            filings.append(describe(path))
            continue
        entry = library.get("filings", {}).get(path.name)
        if entry and entry.get("status") in SEARCHABLE:
            overrides = {k: entry[k] for k in ("company", "fiscal_year", "period_end") if entry.get(k)}
            filings.append(replace(describe(path), **overrides))
    return sorted(filings, key=lambda f: (f.company, f.fiscal_year))


def _short_name(registrant: str) -> str:
    """"ADVANCED MICRO DEVICES, INC." -> "Advanced Micro Devices"; "AMAZON.COM, INC." -> "Amazon.com".

    Also cleans what web filings printed to PDF add: fill-in underlines and stray punctuation
    (". ____ Walmart Inc." -> "Walmart"), and SEC name suffixes ("COSTCO WHOLESALE CORP /NEW/").
    """
    name = re.sub(r"_+", " ", registrant)
    name = re.sub(r"\s*/[A-Z]{1,4}/?\s*$", "", name.strip())
    name = re.sub(r"\s+", " ", name).strip(" .,;:-")
    name = re.sub(r",?\s+(&\s+)?(inc|corp|corporation|co|ltd|plc|llc)\.?$", "", name, flags=re.I)
    if any(c.islower() for c in name):  # already written in normal case, e.g. "Apple Inc."
        return name
    return " ".join(w if w in _KEEP_CAPS else w.capitalize() for w in name.split())


# Other names people use for a company, matched as whole words, ignoring case, except aliases that are
# also ordinary words (so "Chase" the bank doesn't match "chase").
_ALIASES = {
    "Advanced Micro Devices": ["AMD"],
    "Amazon.com": ["Amazon", "AWS", "AMZN"],
    "Apple": ["AAPL"],
    "JPMorgan Chase": ["JPMorgan", "JP Morgan", "J.P. Morgan", "JPM", "Chase"],
    "Microsoft": ["MSFT"],
    "NVIDIA": ["NVDA"],
    "Tesla": ["TSLA"],
}
_CASE_SENSITIVE_ALIASES = {"Chase"}


def aliases_for(company: str, folder: Path = FILINGS_DIR) -> list[str]:
    """Other names for a company: the built-in list, plus whatever the library learned when filings were
    added (the name the user typed, the SEC ticker), so new companies need no code changes."""
    names = list(_ALIASES.get(company, []))
    for entry in ((read_library(folder) or {}).get("filings") or {}).values():
        if entry.get("company") == company:
            names += [a for a in entry.get("aliases", []) if a and a != company and a not in names]
    return names


def _mentions(text: str, name: str) -> bool:
    flags = 0 if name in _CASE_SENSITIVE_ALIASES else re.I
    return re.search(rf"(?<![\w.]){re.escape(name)}(?!\w)", text, flags) is not None


def companies_in(text: str, folder: Path = FILINGS_DIR) -> list[str]:
    """Companies with filings in the folder that `text` names, e.g. "Compare Apple and MSFT" -> [Apple, Microsoft]."""
    return [
        company
        for company in sorted({f.company for f in list_filings(folder)})
        if any(_mentions(text, name) for name in [company, *aliases_for(company, folder)])
    ]


def resolve_company(name: str, folder: Path = FILINGS_DIR) -> str | None:
    """A company name or alias -> the company label used in the filings, e.g. "amd" -> "Advanced Micro Devices"."""
    wanted = name.strip().lower()
    for company in {f.company for f in list_filings(folder)}:
        if wanted in [n.lower() for n in [company, *aliases_for(company, folder)]]:
            return company
    return None


def files_for(company: str, folder: Path = FILINGS_DIR) -> list[str]:
    return [f.file for f in list_filings(folder) if f.company == company]


def format_filings(folder: Path = FILINGS_DIR) -> str:
    return "\n".join(
        f"- {f.label} | fiscal year ended {f.period_end} | {f.pages} pages | file: {f.file}" for f in list_filings(folder)
    )
