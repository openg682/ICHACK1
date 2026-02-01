"""
Charity Intelligence Map — Data Sources
========================================
Handles downloading, caching, and parsing of raw data from the
Charity Commission for England & Wales bulk data extract.

Data source: https://register-of-charities.charitycommission.gov.uk
Licence:     Open Government Licence v3.0
"""

import os
import csv
import sys
import zipfile
from urllib.request import urlretrieve
from urllib.error import URLError
from typing import Optional, List, Dict
csv.field_size_limit(sys.maxsize)
from backend.config import DATASETS, DATA_DIR
from backend.models import Charity, AnnualReturn


# ═══════════════════════════════════════════════════════════════════════════
# DOWNLOADING
# ═══════════════════════════════════════════════════════════════════════════

def download_all(force: bool = False) -> Dict[str, str]:
    """
    Download all configured datasets from the Charity Commission.

    Returns:
        dict mapping dataset name → local file path of extracted text file.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    paths: Dict[str, str] = {}

    for name, info in DATASETS.items():
        txt_path = _download_and_extract(name, info["url"], force=force)
        if txt_path:
            paths[name] = txt_path

    return paths


def _download_and_extract(name: str, url: str, force: bool = False) -> Optional[str]:
    """Download a single dataset ZIP and extract the text file inside."""
    zip_path = os.path.join(DATA_DIR, f"{name}.zip")
    txt_path = os.path.join(DATA_DIR, f"{name}.txt")

    # Use cached extract if available
    if os.path.exists(txt_path) and not force:
        print(f"  ✓ {name} — cached")
        return txt_path

    # Download
    if not os.path.exists(zip_path) or force:
        print(f"  ↓ Downloading {name}...")
        try:
            urlretrieve(url, zip_path)
            size_mb = os.path.getsize(zip_path) / 1e6
            print(f"    {size_mb:.1f} MB downloaded")
        except URLError as e:
            print(f"    ✗ Failed: {e}")
            return None

    # Extract
    print(f"  ⤳ Extracting {name}...")
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.namelist():
                if member.endswith((".txt", ".csv")):
                    _extract_member(z, member, txt_path)
                    return txt_path
            # Fallback: extract first file
            _extract_member(z, z.namelist()[0], txt_path)
            return txt_path
    except Exception as e:
        print(f"    ✗ Extraction failed: {e}")
        return None


def _extract_member(zf: zipfile.ZipFile, member: str, dest: str):
    """Extract a single member from a ZIP archive."""
    with zf.open(member) as src, open(dest, "wb") as dst:
        dst.write(src.read())


# ═══════════════════════════════════════════════════════════════════════════
# PARSING
# ═══════════════════════════════════════════════════════════════════════════

def parse_tsv(filepath: str, max_rows: Optional[int] = None) -> List[Dict]:
    """
    Parse a tab-delimited file into a list of row dictionaries.
    Handles encoding issues gracefully.
    """
    rows: List[Dict] = []
    try:
        with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for i, row in enumerate(reader):
                if max_rows is not None and i >= max_rows:
                    break
                rows.append(row)
    except FileNotFoundError:
        print(f"  ✗ File not found: {filepath}")
    return rows


def safe_float(val, default: float = 0.0) -> float:
    """Safely convert a string value to float."""
    if val is None:
        return default
    try:
        cleaned = str(val).strip().replace(",", "").replace("£", "")
        if cleaned in ("", "-", "N/A", "None"):
            return default
        return float(cleaned)
    except (ValueError, TypeError):
        return default


def safe_int(val, default: int = 0) -> int:
    """Safely convert a string value to int."""
    return int(safe_float(val, float(default)))


# ═══════════════════════════════════════════════════════════════════════════
# LOADING INTO MODELS
# ═══════════════════════════════════════════════════════════════════════════

def load_charities(region: Optional[str] = None) -> Dict[str, Charity]:
    """
    Load the main charity register and return indexed by charity number.

    Args:
        region: Optional filter — currently supports "london".
    """
    from backend.config import LONDON_OUTWARD

    filepath = os.path.join(DATA_DIR, "charity.txt")
    raw = parse_tsv(filepath)
    print(f"  Loaded {len(raw)} raw charity records")

    charities: Dict[str, Charity] = {}

    for row in raw:
        status = (row.get("charity_registration_status") or "").strip().lower()
        if status != "registered":
            continue

        num = (row.get("registered_charity_number") or "").strip()
        if not num:
            continue

        name = (row.get("charity_name") or "").strip()
        if not name:
            continue

        postcode = (row.get("charity_contact_postcode") or "").strip().upper()

        # Region filter
        if region == "london":
            outward = postcode.split()[0] if " " in postcode else postcode[: len(postcode) - 3].strip()
            if outward not in LONDON_OUTWARD:
                continue

        charities[num] = Charity(
            charity_number=num,
            name=name,
            postcode=postcode,
            income=safe_float(row.get("latest_income")),
            spending=safe_float(row.get("latest_expenditure")),
            date_registered=(row.get("date_of_registration") or "").strip(),
            date_removed=(row.get("date_of_removal") or "").strip(),
            activities=(row.get("charity_activities") or "").strip()[:300],
            company_number=(row.get("charity_company_registration_number") or "").strip(),
            reporting_status=(row.get("charity_reporting_status") or "").strip(),
        )

    print(f"  Active registered charities: {len(charities)}")
    return charities


def load_classifications(charities: Dict[str, Charity]) -> None:
    """Load classification data and attach to charity objects (mutates in-place)."""
    from backend.config import CLASSIFICATION_WHAT, CLASSIFICATION_WHO, CLASSIFICATION_HOW

    filepath = os.path.join(DATA_DIR, "charity_classification.txt")
    rows = parse_tsv(filepath)
    print(f"  Loaded {len(rows)} classification records")

    lookup = {"What": CLASSIFICATION_WHAT, "Who": CLASSIFICATION_WHO, "How": CLASSIFICATION_HOW}

    for row in rows:
        num = (row.get("registered_charity_number") or "").strip()
        if num not in charities:
            continue

        cls_type = (row.get("classification_type") or "").strip()
        cls_code = (row.get("classification_code") or "").strip()
        cls_desc = (row.get("classification_description") or "").strip()
        label = cls_desc or lookup.get(cls_type, {}).get(cls_code, "Unknown")

        c = charities[num]
        if cls_type == "What":
            c.categories.append(label)
        elif cls_type == "Who":
            c.beneficiaries.append(label)
        elif cls_type == "How":
            c.methods.append(label)


def load_annual_returns(charities: Dict[str, Charity]) -> None:
    """Load annual return history and attach to charity objects."""
    filepath = os.path.join(DATA_DIR, "charity_annual_return_history.txt")
    rows = parse_tsv(filepath)
    print(f"  Loaded {len(rows)} annual return records")

    for row in rows:
        num = (row.get("registered_charity_number") or "").strip()
        if num not in charities:
            continue

        charities[num].annual_returns.append(
            AnnualReturn(
                fin_period_end=(row.get("fin_period_end_date") or "").strip(),
                income=safe_float(row.get("total_gross_income")),
                spending=safe_float(row.get("total_gross_expenditure")),
                ar_cycle=(row.get("ar_cycle_reference") or "").strip(),
            )
        )


def load_parta_returns(charities: Dict[str, Charity]) -> None:
    """
    Load Part A annual returns (reserves, employees, volunteers).
    Keeps only the latest return per charity.
    """
    filepath = os.path.join(DATA_DIR, "charity_annual_return_parta.txt")
    rows = parse_tsv(filepath)
    print(f"  Loaded {len(rows)} Part A records")

    # Track latest per charity
    latest: Dict[str, Dict] = {}

    for row in rows:
        num = (row.get("registered_charity_number") or "").strip()
        if num not in charities:
            continue

        fin_end = (row.get("fin_period_end_date") or "").strip()
        if num not in latest or fin_end > latest[num]["fin_end"]:
            latest[num] = {
                "fin_end": fin_end,
                "income": safe_float(row.get("total_gross_income")),
                "spending": safe_float(row.get("total_gross_expenditure")),
                "reserves": safe_float(row.get("reserves")),
                "employees": safe_int(row.get("count_employees")),
                "volunteers": safe_int(row.get("count_volunteers")),
            }

    # Merge into charity objects
    for num, pa in latest.items():
        c = charities[num]
        c.reserves = pa["reserves"]
        c.employees = pa["employees"]
        c.volunteers = pa["volunteers"]
        if pa["income"] > 0:
            c.income = pa["income"]
        if pa["spending"] > 0:
            c.spending = pa["spending"]


def load_areas_of_operation(charities: Dict[str, Charity]) -> None:
    """Load geographic areas of operation and attach to charity objects."""
    filepath = os.path.join(DATA_DIR, "charity_area_of_operation.txt")
    rows = parse_tsv(filepath)
    print(f"  Loaded {len(rows)} area records")

    for row in rows:
        num = (row.get("registered_charity_number") or "").strip()
        if num not in charities:
            continue
        area = (row.get("geographic_area_description") or "").strip()
        if area:
            charities[num].area_of_operation.append(area)
