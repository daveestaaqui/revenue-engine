"""Tennessee official county delinquent tax sale excess proceeds scrapers (T.C.A. § 67-5-2702)."""

from __future__ import annotations

import io
import re
import urllib.parse
from datetime import datetime, timezone
import pypdf
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_mmddyyyy(raw: str) -> str:
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", raw.strip().rstrip("*"))
    if not m:
        return ""
    mm, dd, yyyy = m.groups()
    return f"{int(yyyy):04d}-{int(mm):02d}-{int(dd):02d}"


def _fetch_davidson_county() -> list[dict]:
    """Fetch Davidson County (Metro Nashville) Chancery Court Clerk & Master Excess Proceeds PDF."""
    schedule_url = "https://chanceryclerkandmaster.nashville.gov/fees/property-tax-schedule/"
    pdf_url = "https://chanceryclerkandmaster.nashville.gov/wp-content/uploads/Excess-Proceeds-updated-10-15.pdf"
    try:
        r_idx = requests.get(schedule_url, headers=HEADERS, timeout=20)
        if r_idx.status_code == 200:
            soup = BeautifulSoup(r_idx.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if re.search(r"excess[-_ ]?proceeds", href, re.I) and href.lower().endswith(".pdf"):
                    pdf_url = urllib.parse.urljoin(schedule_url, href)
                    break
    except Exception as exc:
        print(f"[tn.davidson.index] warning: {exc}")

    r_pdf = requests.get(pdf_url, headers=HEADERS, timeout=30)
    r_pdf.raise_for_status()

    reader = pypdf.PdfReader(io.BytesIO(r_pdf.content))
    full_text = "\n".join((p.extract_text() or "") for p in reader.pages)
    retrieved_at = _now_iso()

    row_re = re.compile(
        r"^(\d{2}-\d{3,4}-[IVX]+)\s+([A-Z0-9]+)\s+(.+?)\s+([\d,]+\.\d{2})\$?\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}/\d{1,2}/\d{4})\*?",
        re.MULTILINE,
    )

    records: list[dict] = []
    for m in row_re.finditer(full_text):
        case_no, parcel_id, taxpayer, amt_str, _held_since, _recent_act, order_date = m.groups()
        try:
            balance = float(amt_str.replace(",", ""))
        except ValueError:
            continue
        if balance <= 0:
            continue

        docket_id = f"{case_no}-{parcel_id}"
        verify_url = f"{pdf_url}#search={urllib.parse.quote(parcel_id)}"
        records.append({
            "State": "TN",
            "County": "Davidson",
            "Case_or_TaxDeed_No": docket_id,
            "Parcel_ID": parcel_id,
            "Owner_Name": re.sub(r"\s+", " ", taxpayer).strip(),
            "Property_Address": f"Parcel {parcel_id}, Metropolitan Nashville & Davidson County, TN",
            "Surplus_Balance_USD": round(balance, 2),
            "Sale_Date": _parse_mmddyyyy(order_date),
            "Record_Type": "EXCESS_PROCEEDS",
            "Source_URL": pdf_url,
            "Verify_URL": verify_url,
            "Verify_Note": f"Listed on Davidson County Chancery Court Excess Proceeds PDF — Case {case_no}, Parcel {parcel_id}",
            "Retrieved_At": retrieved_at,
        })
    return records


def fetch() -> list[dict]:
    """Download current official Tennessee county excess proceeds lists and parse them."""
    out: list[dict] = []
    for fn in (_fetch_davidson_county,):
        try:
            out.extend(fn())
        except Exception as exc:
            print(f"[tn.{fn.__name__}] skipped due to error: {exc}")
    return out
