"""Florida official county surplus and court registry excess proceeds scrapers."""

from __future__ import annotations

import io
import re
import urllib.parse
from datetime import datetime, timezone
import pandas as pd
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


def _fetch_hillsborough_tax_deed_surplus() -> list[dict]:
    """Fetch Hillsborough County Clerk Weekly Tax Deed Surplus Spreadsheet."""
    index_url = "https://www.hillsclerk.com/taxdeeds"
    xlsx_url = "https://www.hillsclerk.com/documents/d/guest/copy-of-weekly-tax-deed-spreadsheet-25-10-10-xlsx?download=true"
    try:
        resp_idx = requests.get(index_url, headers=HEADERS, timeout=20)
        if resp_idx.status_code == 200:
            soup = BeautifulSoup(resp_idx.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "weekly-tax-deed-spreadsheet" in href.lower():
                    xlsx_url = urllib.parse.urljoin(index_url, href)
                    break
    except Exception as exc:
        print(f"[fl.hillsborough.tax_deed.index] warning: {exc}")

    r = requests.get(xlsx_url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    df = pd.read_excel(io.BytesIO(r.content))
    retrieved_at = _now_iso()

    # Extract "as of MM/DD/YYYY" from column header if present
    sale_date = ""
    first_col = str(df.columns[0])
    m_date = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", first_col)
    if m_date:
        mm, dd, yyyy = m_date.groups()
        sale_date = f"{int(yyyy):04d}-{int(mm):02d}-{int(dd):02d}"

    records: list[dict] = []
    for _, row in df.iterrows():
        case_no = str(row.iloc[0]).strip()
        if not re.match(r"^\d{2}-[A-Z]{2}-\d{4,6}$", case_no):
            continue
        try:
            balance = float(str(row.iloc[1]).replace(",", "").replace("$", "").strip())
        except (ValueError, TypeError):
            continue
        if balance <= 0:
            continue

        records.append({
            "State": "FL",
            "County": "Hillsborough",
            "Case_or_TaxDeed_No": case_no,
            "Parcel_ID": "",
            "Owner_Name": f"Tax Deed Titleholder of Record (File {case_no})",
            "Property_Address": "Hillsborough County Tax Deed Registry Parcel, Tampa, FL",
            "Surplus_Balance_USD": round(balance, 2),
            "Sale_Date": sale_date,
            "Record_Type": "TAX_DEED",
            "Source_URL": xlsx_url,
            "Verify_URL": index_url,
            "Verify_Note": f"Listed on Hillsborough Clerk Weekly Tax Deed Surplus Spreadsheet under Case {case_no}",
            "Retrieved_At": retrieved_at,
        })
    return records


def _fetch_hillsborough_court_registry() -> list[dict]:
    """Fetch Hillsborough County Clerk Daily Circuit Civil Court Registry Balances PDF."""
    dir_url = "https://publicrec.hillsclerk.com/Civil/registry_trust_balances/"
    r_dir = requests.get(dir_url, headers=HEADERS, timeout=20)
    r_dir.raise_for_status()
    soup = BeautifulSoup(r_dir.text, "html.parser")

    pdf_links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "Registry_and_TrustAccounts_Balances_as_of_" in href and href.lower().endswith(".pdf"):
            pdf_links.append(urllib.parse.urljoin(dir_url, href))

    if not pdf_links:
        return []

    # Pick the most recent PDF chronologically by (YYYY, MM, DD) in filename
    def _pdf_date_key(u: str) -> tuple[str, str, str, str]:
        m_dt = re.search(r"(\d{2})_(\d{2})_(\d{4})\.pdf$", u)
        if m_dt:
            mm, dd, yyyy = m_dt.groups()
            return (yyyy, mm, dd, u)
        return ("0000", "00", "00", u)

    pdf_url = sorted(pdf_links, key=_pdf_date_key)[-1]
    r_pdf = requests.get(pdf_url, headers=HEADERS, timeout=30)
    r_pdf.raise_for_status()

    reader = pypdf.PdfReader(io.BytesIO(r_pdf.content))
    retrieved_at = _now_iso()

    # Extract report date from filename if possible (e.g. _10_15_2026.pdf)
    report_date = ""
    m_fn = re.search(r"(\d{2})_(\d{2})_(\d{4})\.pdf$", pdf_url)
    if m_fn:
        mm, dd, yyyy = m_fn.groups()
        report_date = f"{yyyy}-{mm}-{dd}"

    line_re = re.compile(
        r"^(\d{2}-CA-\d{6})\s+(.+?)\s*\$?([\d,]+\.\d{2})(?:\s+\$?([\d,]+\.\d{2}))?(?:\s+\$?([\d,]+\.\d{2}))?$",
        re.MULTILINE,
    )
    clerk_officials_re = re.compile(
        r"\b(STUART,\s*CINDY|CINDY\s+STUART|PAT\s+FRANK|VICTOR\s+CRIST|CLERK\s+OF\s+THE\s+CIRCUIT\s+COURT)\b",
        re.IGNORECASE,
    )

    records: list[dict] = []
    seen_cases: set[str] = set()
    for page in reader.pages:
        txt = page.extract_text() or ""
        for m in line_re.finditer(txt):
            case_no = m.group(1).strip()
            if case_no in seen_cases:
                continue
            party = re.sub(r"\s+", " ", m.group(2)).strip(" .,-;")
            if clerk_officials_re.search(party):
                continue
            # Net credit balance is the last monetary column on the line
            amounts = [g for g in (m.group(3), m.group(4), m.group(5)) if g]
            if not amounts:
                continue
            try:
                balance = float(amounts[-1].replace(",", ""))
            except ValueError:
                continue
            if balance <= 0:
                continue
            seen_cases.add(case_no)
            verify_url = f"{pdf_url}#search={urllib.parse.quote(case_no)}"
            records.append({
                "State": "FL",
                "County": "Hillsborough",
                "Case_or_TaxDeed_No": case_no,
                "Parcel_ID": "",
                "Owner_Name": party,
                "Property_Address": "Hillsborough County Circuit Civil Registry, Tampa, FL",
                "Surplus_Balance_USD": round(balance, 2),
                "Sale_Date": report_date,
                "Record_Type": "FORECLOSURE",
                "Source_URL": pdf_url,
                "Verify_URL": verify_url,
                "Verify_Note": f"Listed on Hillsborough Clerk Court Registry Balances PDF — Case {case_no}",
                "Retrieved_At": retrieved_at,
            })
    return records


def fetch() -> list[dict]:
    """Download current official Florida county surplus/registry lists and parse them."""
    from compliance.ground_truth_gatekeeper import GroundTruthGatekeeper
    out: list[dict] = []
    for fn in (_fetch_hillsborough_tax_deed_surplus, _fetch_hillsborough_court_registry):
        try:
            for rec in fn():
                ok, _ = GroundTruthGatekeeper.validate_lead_record(rec)
                if ok:
                    out.append(rec)
        except Exception as exc:
            print(f"[fl.{fn.__name__}] skipped due to error: {exc}")
    return out
