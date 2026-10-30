"""Fetch a 10-K from the SEC's EDGAR (D-024).

The SEC requires automated requests to identify a contact (sec.gov/os/accessing-edgar-data). IndexIt sends
the one saved in the app's settings, only to sec.gov, and never shows or logs it. EDGAR publishes 10-Ks as
web pages, so the filing is printed to PDF with Chrome: page citations work exactly as for uploads.
"""

import base64
import json
import mimetypes
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from indexit.library import sec_contact

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
MAX_IMAGES = 80


class SecError(Exception):
    """A problem worth showing the user as is (never contains the contact)."""


def _get(url: str) -> bytes:
    contact = sec_contact()
    if not contact:
        raise SecError("Add your SEC contact email first.")
    request = urllib.request.Request(url, headers={"User-Agent": f"IndexIt personal research tool {contact}"})
    time.sleep(0.12)  # the SEC allows 10 requests a second
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code == 403:
            raise SecError("The SEC refused the request. Check the contact email in settings.") from None
        raise SecError(f"The SEC returned an error ({error.code}) for {url}.") from None
    except urllib.error.URLError:
        raise SecError("Couldn't reach the SEC. Are you online?") from None


def find_company(name: str) -> dict:
    """A company name or ticker -> the SEC's record: {"cik", "ticker", "title"}."""
    wanted = name.strip().lower()
    companies = list(json.loads(_get(TICKERS_URL)).values())
    for c in companies:
        if c["ticker"].lower() == wanted:
            return {"cik": int(c["cik_str"]), "ticker": c["ticker"], "title": c["title"]}
    matches = [c for c in companies if re.search(rf"(?<!\w){re.escape(wanted)}(?!\w)", c["title"].lower())]
    if not matches:
        raise SecError(f'Couldn\'t find "{name}" at the SEC. Try its legal name or ticker (e.g. "Alphabet" or "GOOGL").')
    best = min(matches, key=lambda c: len(c["title"]))  # "Costco" -> "COSTCO WHOLESALE CORP /NEW"
    return {"cik": int(best["cik_str"]), "ticker": best["ticker"], "title": best["title"]}


def find_10k(company: dict, year: int) -> dict:
    """The 10-K for a fiscal year, labelled as IndexIt does: by the year the fiscal year ends in."""
    recent = json.loads(_get(SUBMISSIONS_URL.format(cik=company["cik"])))["filings"]["recent"]
    found = []
    for i, form in enumerate(recent["form"]):
        if form != "10-K":
            continue
        report_date = recent["reportDate"][i]
        found.append(int(report_date[:4]))
        if report_date.startswith(str(year)):
            return {"accession": recent["accessionNumber"][i], "document": recent["primaryDocument"][i],
                    "report_date": report_date, "filing_date": recent["filingDate"][i]}
    years = ", ".join(f"FY{y}" for y in sorted(set(found), reverse=True)[:6]) or "none"
    raise SecError(f"No FY{year} 10-K found for {company['title']}. Recent 10-Ks at the SEC: {years}.")


def _inline_images(html: str, base_url: str) -> str:
    """Chrome prints without the SEC contact header, so it can't load the filing's images itself."""
    sources = list(dict.fromkeys(re.findall(r'<img[^>]+src="([^"]+)"', html, re.I)))[:MAX_IMAGES]
    for src in sources:
        if src.startswith("data:"):
            continue
        try:
            data = _get(src if src.startswith("http") else base_url + src)
        except SecError:
            continue
        mime = mimetypes.guess_type(src)[0] or "image/jpeg"
        html = html.replace(f'"{src}"', f'"data:{mime};base64,{base64.b64encode(data).decode()}"')
    return html


def fetch(company_name: str, year: int) -> tuple[bytes, str, dict]:
    """Download a 10-K and print it to PDF. Returns (pdf bytes, file name, details for the card)."""
    if not CHROME.exists():
        raise SecError("Fetching from the SEC needs Google Chrome (it prints the filing to PDF).")
    company = find_company(company_name)
    filing = find_10k(company, year)
    base_url = ARCHIVE_URL.format(cik=company["cik"], accession=filing["accession"].replace("-", ""))
    html = _inline_images(_get(base_url + filing["document"]).decode("utf-8", "replace"), base_url)
    with tempfile.TemporaryDirectory() as tmp:
        page, pdf = Path(tmp) / "filing.html", Path(tmp) / "filing.pdf"
        page.write_text(html)
        subprocess.run(
            [str(CHROME), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={tmp}/chrome",
             f"--print-to-pdf={pdf}", page.as_uri()],
            capture_output=True, timeout=300,
        )
        if not pdf.exists():
            raise SecError("Couldn't turn the SEC filing into a PDF.")
        data = pdf.read_bytes()
    name = f"{company['ticker']} 10-K FY{year} (filed {filing['filing_date']}).pdf"
    details = {"ticker": company["ticker"], "title": company["title"], "cik": company["cik"],
               "url": base_url + filing["document"], **filing}
    return data, name, details
