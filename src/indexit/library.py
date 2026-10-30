"""The filings library (D-024): add a filing (upload or SEC fetch) -> confirm its card -> index it -> remove it.

Added files wait in data/incoming/<id>/ until confirmed, then move into the library folder. Indexing runs
in a separate process, one filing at a time (Docling needs a few GB; an 8 GB Mac can't run several): text
first, so the filing is searchable in about 30 s, then Docling tables (~1.3 s/page).

  python -m indexit.library index <file>   # what the app runs per filing; prints JSON progress lines
"""

import json
import os
import re
import secrets
import shutil
import sys
import time
from pathlib import Path

import pymupdf

from indexit.documents import (
    FILINGS_DIR, PROJECT_DIR, SEARCHABLE, _short_name, aliases_for, describe, read_library, write_library,
)
from indexit.store import file_hash

INCOMING_DIR = PROJECT_DIR / "data" / "incoming"
REMOVED_DIR = FILINGS_DIR / "removed"
SETTINGS_FILE = PROJECT_DIR / "data" / "settings.json"  # the SEC contact: read by code only, never sent to the page
MAX_UPLOAD_BYTES = 150 * 1024 * 1024


def library() -> dict:
    return read_library() or {"filings": {}}


def active_filings() -> dict[str, dict]:
    return {name: e for name, e in library()["filings"].items() if e.get("status") != "removed"}


def _new_id() -> str:
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}"


def _safe_name(name: str) -> str:
    name = re.sub(r"[^\w .,()&'\-\[\]]", "_", Path(name).name).strip(" ._") or "filing"
    return name if name.lower().endswith(".pdf") else f"{name}.pdf"


def _unique(folder: Path, name: str) -> str:
    stem, n = Path(name).stem, 2
    while (folder / name).exists():
        name, n = f"{stem} ({n}).pdf", n + 1
    return name


def _words(name: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", name.lower().replace("&", "and"))


def _library_company(names: list[str | None], ticker: str | None) -> str | None:
    """The name the library already uses for this company, so a new year joins the same company
    (the SEC calls Amazon "AMAZON COM INC"; the library says "Amazon.com")."""
    for company in {e["company"] for e in active_filings().values()}:
        if ticker and ticker.lower() in [a.lower() for a in aliases_for(company)]:
            return company
        if any(n and _words(n) == _words(company) for n in names):
            return company
    return None


def _same_company(entered: str, found: str) -> bool:
    a, b = _words(entered), _words(found)
    return bool(a) and (a in b or b in a or entered.lower() in [x.lower() for x in aliases_for(found)])


# ---------- Adding: stage -> card -> confirm / cancel ----------

def stage(data: bytes, filename: str, company: str, year: int | None, source: str, sec: dict | None = None) -> dict:
    """Save an added PDF in data/incoming/<id>/ and return its confirmation card."""
    staged_id = _new_id()
    folder = INCOMING_DIR / staged_id
    folder.mkdir(parents=True)
    path = folder / _safe_name(filename)
    path.write_bytes(data)
    card = check(path, company, year, source, sec)
    card["id"] = staged_id
    (folder / "card.json").write_text(json.dumps(card, indent=1))
    return card


def check(path: Path, company: str, year: int | None, source: str, sec: dict | None = None) -> dict:
    """What IndexIt read from the PDF, cross-checked against what the user typed, with warnings."""
    try:
        with pymupdf.open(path) as pdf:
            pages = len(pdf)
            first = " ".join(pdf[i].get_text() for i in range(min(3, pages)))
            text_chars = sum(len(pdf[i].get_text().strip()) for i in range(min(10, pages)))
    except Exception:
        return {"file": path.name, "source": source, "blocking": True, "warnings": ["This file isn't a readable PDF."],
                "entered": {"company": company, "year": year}, "cover": {}, "pages": 0}
    cover = describe(path)
    found_company = (cover.company if cover.company != path.stem else None) or None
    sec_name = _short_name(sec["title"]) if sec else None  # the SEC's name is authoritative for fetches
    found_year = cover.fiscal_year or None
    period_end = cover.period_end if found_year else (sec or {}).get("report_date", "unknown")
    if not found_year and sec:
        found_year = int(sec["report_date"][:4])
    final_company = (_library_company([sec_name, found_company, company], (sec or {}).get("ticker"))
                     or sec_name or found_company or company.strip())
    final_year = found_year or year

    warnings, blocking = [], False
    if text_chars < 1000:
        warnings.append("This PDF has almost no text (it may be a scan). IndexIt can't read scanned pages yet.")
        blocking = True
    if not re.search(r"10-K", first):
        warnings.append('This doesn\'t look like a 10-K: its first pages never mention "10-K".')
    if found_year and year and found_year != year:
        warnings.append(f"You said {year}, but the cover says the fiscal year ended {period_end} "
                        f"(IndexIt calls that FY{found_year}).")
    if found_company and company and not _same_company(company, found_company):
        warnings.append(f'You said "{company}", but the cover names "{found_company}".')
    if not (found_company and found_year):
        warnings.append("IndexIt couldn't read the company or fiscal year from the cover. Check them below.")
    digest = file_hash(path)
    filings = active_filings()
    duplicate = next((n for n, e in filings.items() if e.get("hash") == digest), None)
    if duplicate:
        e = filings[duplicate]
        warnings.append(f"This exact file is already in the library ({e['company']} FY{e['fiscal_year']}).")
        blocking = True
    elif any(e.get("company") == final_company and e.get("fiscal_year") == final_year for e in filings.values()):
        warnings.append(f"The library already has a {final_company} FY{final_year} 10-K; this would be a second one.")
    years = [e["fiscal_year"] for e in filings.values() if e.get("company") == final_company]
    if final_year and years and final_year < max(years):
        warnings.append(f"Older than the FY{max(years)} filing in the library: answers use the latest one "
                        f"unless you ask about FY{final_year}.")
    return {
        "file": path.name, "source": source, "pages": pages, "hash": digest,
        "entered": {"company": company, "year": year},
        "cover": {"company": found_company, "fiscal_year": cover.fiscal_year or None, "period_end": cover.period_end},
        "company": final_company, "fiscal_year": final_year, "period_end": period_end,
        "sec": sec, "warnings": warnings, "blocking": blocking,
    }


def incoming() -> list[dict]:
    cards = []
    for card_file in sorted(INCOMING_DIR.glob("*/card.json")):
        cards.append(json.loads(card_file.read_text()))
    return cards


def pick_up_dropped_files() -> None:
    """PDFs put straight into the library folder (e.g. in Finder) get a card like any other added file."""
    known = set(library()["filings"])
    for path in FILINGS_DIR.glob("*.pdf"):
        if path.name not in known:
            stage(path.read_bytes(), path.name, "", None, "folder")
            path.unlink()


def confirm(staged_id: str, company: str, year: int) -> str:
    folder = INCOMING_DIR / staged_id
    card = json.loads((folder / "card.json").read_text())
    if card["blocking"]:
        raise ValueError("This file can't be added (see the warnings).")
    company, year = company.strip(), int(year)
    if not company or not 1990 <= year <= 2100:
        raise ValueError("Enter the company name and fiscal year.")
    name = _unique(FILINGS_DIR, card["file"])
    shutil.move(folder / card["file"], FILINGS_DIR / name)
    shutil.rmtree(folder)
    entered = (card["entered"].get("company") or "").strip()
    ticker = (card.get("sec") or {}).get("ticker")
    current = library()
    current["filings"][name] = {
        "company": company, "fiscal_year": year, "period_end": card["period_end"],
        "aliases": [a for a in (entered, ticker) if a and a.lower() != company.lower()],
        "status": "queued", "tables": "pending", "progress": "", "source": card["source"],
        "added": time.strftime("%Y-%m-%d"), "hash": card["hash"], "sec": card.get("sec"),
    }
    write_library(current)
    return name


def cancel(staged_id: str) -> None:
    folder = INCOMING_DIR / staged_id
    card = json.loads((folder / "card.json").read_text())
    if card["source"] == "folder":  # the user's own file: keep it, out of the library's way
        REMOVED_DIR.mkdir(exist_ok=True)
        shutil.move(folder / card["file"], REMOVED_DIR / _unique(REMOVED_DIR, card["file"]))
    shutil.rmtree(folder)


def remove(name: str) -> None:
    """Take a filing out of search; its PDF moves to removed/ (recoverable), never deleted."""
    from indexit.search import TABLE
    from indexit.store import ChunkStore

    current = library()
    entry = current["filings"].get(name)
    if entry is None:
        raise ValueError("Unknown filing.")
    entry.update(status="removed", removed=time.strftime("%Y-%m-%d"))
    write_library(current)
    ChunkStore(TABLE).remove_doc(name)
    if (FILINGS_DIR / name).exists():
        REMOVED_DIR.mkdir(exist_ok=True)
        shutil.move(FILINGS_DIR / name, REMOVED_DIR / _unique(REMOVED_DIR, name))


def update(name: str, **fields) -> None:
    current = library()
    if name in current["filings"]:
        current["filings"][name].update(fields)
        write_library(current)


def unfinished() -> list[str]:
    """Filings whose indexing hasn't finished (e.g. the app was closed mid-way): resumed on start-up."""
    return [n for n, e in active_filings().items()
            if e.get("status") in ("queued", "indexing") or (e.get("status") == "searchable" and e.get("tables") != "failed")]


# ---------- Settings (the SEC contact) ----------

def sec_contact() -> str | None:
    if not SETTINGS_FILE.exists():
        return None
    return json.loads(SETTINGS_FILE.read_text()).get("sec_contact") or None


def save_sec_contact(value: str) -> None:
    value = value.strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        raise ValueError("That doesn't look like an email address.")
    settings = json.loads(SETTINGS_FILE.read_text()) if SETTINGS_FILE.exists() else {}
    settings["sec_contact"] = value
    SETTINGS_FILE.write_text(json.dumps(settings))
    os.chmod(SETTINGS_FILE, 0o600)  # readable by this Mac user only


# ---------- Indexing one filing (runs in its own process) ----------

def index_file(name: str) -> None:
    from indexit import clean_pipeline
    from indexit.cli import store_chunks
    from indexit.embedder import Embedder
    from indexit.search import TABLE
    from indexit.store import ChunkStore
    from indexit.tables import extract_tables

    def emit(event: dict) -> None:
        print(json.dumps(event), flush=True)

    path = FILINGS_DIR / name
    if library()["filings"][name].get("status") not in SEARCHABLE:
        chunks = clean_pipeline.chunk_pdf(path)
        store_chunks(ChunkStore(TABLE), Embedder(), path, chunks, file_hash(path))
        emit({"stage": "searchable", "passages": len(chunks)})
    tables = extract_tables(path, progress=lambda done, total, n: emit(
        {"stage": "tables", "done": done, "total": total, "tables": n}))
    emit({"stage": "ready", "tables": len(tables)})


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "index":
        index_file(sys.argv[2])
    else:
        sys.exit("usage: python -m indexit.library index <file>")
