"""Texas official county excess proceeds scrapers (Tex. Tax Code § 34.04)."""

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
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", raw.strip())
    if not m:
        return ""
    mm, dd, yyyy = m.groups()
    return f"{int(yyyy):04d}-{int(mm):02d}-{int(dd):02d}"


def _fetch_dallas_county() -> list[dict]:
    """Fetch Dallas County District Clerk Current Excess Funds PDF."""
    index_url = "https://www.dallascounty.org/government/district-clerk/public-data.php"
    pdf_url = "https://www.dallascounty.org/Assets/uploads/docs/district-clerk/excess-funds/ExcessFunds-100126.pdf"
    try:
        r_idx = requests.get(index_url, headers=HEADERS, timeout=20)
        if r_idx.status_code == 200:
            soup = BeautifulSoup(r_idx.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if re.search(r"excess[-_ ]?funds", href, re.I) and href.lower().endswith(".pdf"):
                    pdf_url = urllib.parse.urljoin(index_url, href)
                    break
    except Exception as exc:
        print(f"[tx.dallas.index] warning: {exc}")

    r_pdf = requests.get(pdf_url, headers=HEADERS, timeout=30)
    r_pdf.raise_for_status()

    reader = pypdf.PdfReader(io.BytesIO(r_pdf.content))
    full_text = "\n".join((p.extract_text() or "") for p in reader.pages)
    retrieved_at = _now_iso()

    row_re = re.compile(
        r"^((?:TX|DC)-\d{2}-\d{4,6})\s+(.+?)\s+([\d,]+\.\d{2})\$\s+(\d{1,2}/\d{1,2}/\d{4})\s+(?:\d{1,2}/\d{1,2}/\d{4}|N/A)\s+(\d{1,2}/\d{1,2}/\d{4})",
        re.MULTILINE,
    )

    source_suffixes = (
        "CITY OF DALLAS",
        "SHERIFF",
        "CONSTABLE",
        "GARLAND",
        "MESQUITE",
        "IRVING",
        "GRAND PRAIRIE",
        "RICHARDSON",
        "CARROLLTON",
        "FARMERS BRANCH",
        "DESOTO",
        "CEDAR HILL",
        "DUNCANVILLE",
        "LANCASTER",
        "BALCH SPRINGS",
        "ROWLETT",
    )

    records: list[dict] = []
    for m in row_re.finditer(full_text):
        case_no, style_and_src, amt_str, _rcvd_date, sale_date_raw = m.groups()
        try:
            balance = float(amt_str.replace(",", ""))
        except ValueError:
            continue
        if balance <= 0:
            continue

        cleaned = re.sub(r"\s+", " ", style_and_src).strip()
        for sfx in source_suffixes:
            if cleaned.upper().endswith(" " + sfx):
                cleaned = cleaned[: -(len(sfx) + 1)].strip()
                break

        # Extract defendant/former owner from "DALLAS COUNTY et al vs <DEFENDANT>"
        owner = cleaned
        m_vs = re.split(r"\b(?:vs\.?|v\.?)\b", cleaned, maxsplit=1, flags=re.IGNORECASE)
        if len(m_vs) == 2 and m_vs[1].strip():
            owner = m_vs[1].strip()

        verify_url = f"{pdf_url}#search={urllib.parse.quote(case_no)}"
        records.append({
            "State": "TX",
            "County": "Dallas",
            "Case_or_TaxDeed_No": case_no,
            "Parcel_ID": "",
            "Owner_Name": owner,
            "Property_Address": "Dallas County Tax Foreclosure Registry, Dallas, TX",
            "Surplus_Balance_USD": round(balance, 2),
            "Sale_Date": _parse_mmddyyyy(sale_date_raw),
            "Record_Type": "EXCESS_PROCEEDS",
            "Source_URL": pdf_url,
            "Verify_URL": verify_url,
            "Verify_Note": f"Listed on Dallas County District Clerk Current Excess Funds PDF — Case {case_no}",
            "Retrieved_At": retrieved_at,
        })
    return records


def _fetch_fort_bend_county() -> list[dict]:
    """Fetch Fort Bend County District Clerk Eligible Unclaimed Excess Proceeds PDF."""
    pdf_url = "https://odysseyreport.fortbendcountytx.gov/District_Clerk/DC-Eligible-Unclaimed-Excess-Proceeds.pdf"
    r_pdf = requests.get(pdf_url, headers=HEADERS, timeout=30)
    r_pdf.raise_for_status()

    reader = pypdf.PdfReader(io.BytesIO(r_pdf.content))
    full_text = "\n".join((p.extract_text() or "") for p in reader.pages)
    retrieved_at = _now_iso()

    report_date = ""
    m_rpt = re.search(r"Report Time:\s*(\d{1,2}/\d{1,2}/\d{4})", full_text)
    if m_rpt:
        report_date = _parse_mmddyyyy(m_rpt.group(1))

    blocks = re.split(r"(?=\b\d{2}-DCV-\d{5,7}\b)", full_text)
    taxing_unit_re = re.compile(
        r"\b(FBISD|ISD|INDEPENDENT\s+SCHOOL|FORT\s+BEND|CITY\s+OF|STATE\s+OF|MUD\b|LID\b|WCID\b|CAD\b|TAX\s+ASSESSOR|COUNTY|LEVEE|DRAINAGE|MUNICIPAL|UTILITY|ASSOCIATION|HOA|POA|INC\b|LLC\b|CORP\b|BANK\b|MORTGAGE)\b",
        re.IGNORECASE,
    )
    prefix_re = re.compile(
        r"^(?:Re-)?(?:Notice\s+of\s+Excess\s+Proceeds\s+for|Notice\s+Sent\s+to|Notice\s+for|Excess\s+Proceeds\s+for|Mailed\s+To)\s+",
        re.IGNORECASE,
    )

    case_map: dict[str, dict] = {}
    for blk in blocks:
        lines = [ln.strip() for ln in blk.splitlines() if ln.strip()]
        if len(lines) < 3:
            continue
        case_no = lines[0]
        if not re.match(r"^\d{2}-DCV-\d{5,7}$", case_no):
            continue
        amt_line = lines[1].lstrip("$").replace(",", "").strip()
        try:
            balance = float(amt_line)
        except ValueError:
            continue
        if balance <= 0:
            continue

        entry = case_map.setdefault(case_no, {"balance": balance, "candidates": [], "all_names": []})
        for raw_ln in lines[2:]:
            if raw_ln.startswith("Page ") or "Report Time:" in raw_ln or "Case Number" in raw_ln:
                continue
            if not prefix_re.search(raw_ln):
                continue
            cleaned_name = prefix_re.sub("", raw_ln).strip()
            cleaned_name = re.sub(r"\s*\(In\s+Rem(?:\s+Only)?\)", "", cleaned_name, flags=re.IGNORECASE).strip()
            cleaned_name = re.sub(r"\s+", " ", cleaned_name).strip(" ,;-")
            if not cleaned_name:
                continue
            if cleaned_name not in entry["all_names"]:
                entry["all_names"].append(cleaned_name)
            if not taxing_unit_re.search(cleaned_name) and cleaned_name not in entry["candidates"]:
                entry["candidates"].append(cleaned_name)

    records: list[dict] = []
    for case_no, info in case_map.items():
        if info["candidates"]:
            owner = " / ".join(info["candidates"][:2])
        elif info["all_names"]:
            owner = info["all_names"][0]
        else:
            continue

        verify_url = f"{pdf_url}#search={urllib.parse.quote(case_no)}"
        records.append({
            "State": "TX",
            "County": "Fort Bend",
            "Case_or_TaxDeed_No": case_no,
            "Parcel_ID": "",
            "Owner_Name": owner,
            "Property_Address": "Fort Bend County District Court Registry, Richmond, TX",
            "Surplus_Balance_USD": round(info["balance"], 2),
            "Sale_Date": report_date,
            "Record_Type": "EXCESS_PROCEEDS",
            "Source_URL": pdf_url,
            "Verify_URL": verify_url,
            "Verify_Note": f"Listed on Fort Bend County District Clerk Excess Proceeds PDF — Case {case_no}",
            "Retrieved_At": retrieved_at,
        })
    return records


def fetch() -> list[dict]:
    """Download current official Texas county excess proceeds lists and parse them."""
    out: list[dict] = []
    for fn in (_fetch_dallas_county, _fetch_fort_bend_county):
        try:
            out.extend(fn())
        except Exception as exc:
            print(f"[tx.{fn.__name__}] skipped due to error: {exc}")
    return out
