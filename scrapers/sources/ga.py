"""Georgia official county tax-sale excess funds scrapers (O.C.G.A. § 48-4-5)."""

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

DEKALB_CITIES = (
    "AVONDALE ESTATES",
    "STONE MOUNTAIN",
    "PINE LAKE",
    "CHAMBLEE",
    "CLARKSTON",
    "DORAVILLE",
    "DUNWOODY",
    "ELLENWOOD",
    "LITHONIA",
    "CONLEY",
    "DECATUR",
    "ATLANTA",
    "TUCKER",
    "SCOTTDALE",
    "REDAN",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_mmddyyyy(raw: str) -> str:
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", raw.strip())
    if not m:
        return ""
    mm, dd, yyyy = m.groups()
    return f"{int(yyyy):04d}-{int(mm):02d}-{int(dd):02d}"


def _parse_month_year(raw: str) -> str:
    try:
        dt = datetime.strptime(raw.strip(), "%B %Y")
        return dt.strftime("%Y-%m-01")
    except Exception:
        return ""


def _fetch_dekalb_county() -> list[dict]:
    """Fetch DeKalb County Tax Commissioner Excess Funds List PDF."""
    index_url = "https://dekalbtaxga.gov/property-tax/delinquent-taxes/"
    pdf_url = "https://dekalbtaxga.gov/wp-content/uploads/Excess-Funds-List.pdf"
    try:
        r_idx = requests.get(index_url, headers=HEADERS, timeout=20)
        if r_idx.status_code == 200:
            soup = BeautifulSoup(r_idx.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "excess-funds-list" in href.lower() and href.lower().endswith(".pdf"):
                    pdf_url = urllib.parse.urljoin(index_url, href)
                    break
    except Exception as exc:
        print(f"[ga.dekalb.index] warning: {exc}")

    r_pdf = requests.get(pdf_url, headers=HEADERS, timeout=30)
    r_pdf.raise_for_status()

    reader = pypdf.PdfReader(io.BytesIO(r_pdf.content))
    full_text = "\n".join((p.extract_text() or "") for p in reader.pages)
    retrieved_at = _now_iso()

    row_re = re.compile(
        r"^(\d{2}\s+\d{3}\s+\d{2}\s+\d{3})\s+\$([\d,]+\.\d{2})\s+(\d{1,2}/\d{1,2}/\d{4})\s+(.+)$",
        re.MULTILINE,
    )

    records: list[dict] = []
    for m in row_re.finditer(full_text):
        parcel_id, amt_str, sale_date_raw, tail = m.groups()
        try:
            balance = float(amt_str.replace(",", ""))
        except ValueError:
            continue
        if balance <= 0:
            continue

        tail_clean = re.sub(r"\s+", " ", tail).strip()
        # Split owner name from street number in situs address
        owner = tail_clean
        address = "DeKalb County, GA"
        m_addr = re.search(r"\s+(\d+\s+[A-Z0-9\s\.\-]+?\s+30\d{3})$", tail_clean)
        if m_addr:
            owner = tail_clean[: m_addr.start()].strip()
            raw_addr = m_addr.group(1).strip()
            for city in DEKALB_CITIES:
                pat = rf"\s+({city})\s+(30\d{{3}})$"
                mc = re.search(pat, raw_addr, flags=re.IGNORECASE)
                if mc:
                    street = raw_addr[: mc.start()].strip()
                    address = f"{street}, {mc.group(1).title()}, GA {mc.group(2)}"
                    break
            else:
                address = f"{raw_addr}, GA"

        parcel_compact = parcel_id.replace(" ", "-")
        verify_url = f"{pdf_url}#search={urllib.parse.quote(parcel_id)}"
        records.append({
            "State": "GA",
            "County": "DeKalb",
            "Case_or_TaxDeed_No": f"DK-{parcel_compact}",
            "Parcel_ID": parcel_id,
            "Owner_Name": owner,
            "Property_Address": address,
            "Surplus_Balance_USD": round(balance, 2),
            "Sale_Date": _parse_mmddyyyy(sale_date_raw),
            "Record_Type": "TAX_DEED",
            "Source_URL": pdf_url,
            "Verify_URL": verify_url,
            "Verify_Note": f"Listed on DeKalb County Tax Commissioner Excess Funds PDF — Parcel {parcel_id}",
            "Retrieved_At": retrieved_at,
        })
    return records


def _fetch_gwinnett_county() -> list[dict]:
    """Fetch Gwinnett County Tax Commissioner Excess Funds All Years PDF."""
    index_url = "https://www.gwinnetttaxcommissioner.com/property-tax/tax-sale-excess-funds"
    pdf_url = "https://www.gwinnetttaxcommissioner.com/documents/d/egov/excess-funds-all-years?download=true"
    r_pdf = requests.get(pdf_url, headers=HEADERS, timeout=30)
    r_pdf.raise_for_status()

    reader = pypdf.PdfReader(io.BytesIO(r_pdf.content))
    full_text = "\n".join((p.extract_text() or "") for p in reader.pages)
    retrieved_at = _now_iso()

    row_re = re.compile(
        r"^.+?\s+(R\d{4}(?:\s+\d{3}[A-Z]?|[A-Z]\d{3}))\s+(.+?)\s+\$([\d,]+\.\d{2})\s+([A-Za-z]+\s+\d{4})\s*$",
        re.MULTILINE,
    )

    records: list[dict] = []
    for m in row_re.finditer(full_text):
        parcel_id, owner_and_situs, amt_str, month_year = m.groups()
        try:
            balance = float(amt_str.replace(",", ""))
        except ValueError:
            continue
        if balance <= 0:
            continue

        mid = re.sub(r"\s+", " ", owner_and_situs).strip()
        owner = mid
        situs = "Gwinnett County, GA"
        m_num = re.search(r"\s+(\d+\s+[A-Z0-9\s\.\-]+)$", mid)
        if m_num:
            owner = mid[: m_num.start()].strip()
            situs = f"{m_num.group(1).strip()}, Gwinnett County, GA"
        else:
            # Situs without street number (e.g. "WALLACE CIR", "BOULDER STONE WAY")
            m_st = re.search(
                r"\s+([A-Z0-9\s]+\s+(?:RD|DR|CT|LN|WAY|CIR|PL|TRL|TRAIL|BLVD|AVE|ST|HWY|PKWY|GLN))$",
                mid,
            )
            if m_st and m_st.start() > 3:
                owner = mid[: m_st.start()].strip()
                situs = f"{m_st.group(1).strip()}, Gwinnett County, GA"

        parcel_compact = parcel_id.replace(" ", "-")
        inline_pdf_url = "https://www.gwinnetttaxcommissioner.com/documents/d/egov/excess-funds-all-years"
        verify_url = f"{inline_pdf_url}#search={urllib.parse.quote(parcel_id)}"
        records.append({
            "State": "GA",
            "County": "Gwinnett",
            "Case_or_TaxDeed_No": f"GW-{parcel_compact}",
            "Parcel_ID": parcel_id,
            "Owner_Name": owner,
            "Property_Address": situs,
            "Surplus_Balance_USD": round(balance, 2),
            "Sale_Date": _parse_month_year(month_year),
            "Record_Type": "TAX_DEED",
            "Source_URL": pdf_url,
            "Verify_URL": verify_url,
            "Verify_Note": f"Listed on Gwinnett Tax Commissioner Excess Funds PDF — Parcel {parcel_id}",
            "Retrieved_At": retrieved_at,
        })
    return records


def fetch() -> list[dict]:
    """Download current official Georgia county excess funds lists and parse them."""
    out: list[dict] = []
    for fn in (_fetch_dekalb_county, _fetch_gwinnett_county):
        try:
            out.extend(fn())
        except Exception as exc:
            print(f"[ga.{fn.__name__}] skipped due to error: {exc}")
    return out
