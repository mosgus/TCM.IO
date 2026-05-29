"""
CSV / Excel bulk import for TCM Deal Pipeline.

Strict all-or-nothing validation: if ANY row fails validation the entire
import is rejected and nothing is written to the database.
Rows whose Deal Name already exists in the DB are silently skipped.

Test cases (see validate_and_import_csv docstring).
"""

import math
from io import BytesIO

import pandas as pd

# ❗ ignore unresolved references — Streamlit adds main/ to sys.path
from db.mongo import get_mongo_client, get_all_deals, STAGES, STATUSES, STATES

_DB_NAME  = "toccoaIO_db"
_COL_NAME = "deal_pipeline"

_REQUIRED_COLUMNS = [
    "#", "Date Received", "Deal Name", "City", "State", "Zip Code",
    "TCM Originator", "Broker", "Brokerage Company",
    "Fund Investment Amount", "Deal Size",
    "Deal Type", "Deal Subtype", "Asset Class", "Development",
    "Stage", "Status", "Date Closed",
]


# ---------------------------------------------------------------------------
# Field parsers
# ---------------------------------------------------------------------------

def _parse_date(value: str, row_num: int, field: str) -> tuple[str, str | None]:
    """Parse a date string into ISO format (YYYY-MM-DD).

    Accepted formats
    ────────────────
    Dash-separated:
        YYYY-MM-DD   e.g. 2025-12-09
        MM-DD-YYYY   e.g. 12-09-2025
    Slash-separated (MM/DD/YYYY or MM/DD/YY):
        12/9/2025  → 2025-12-09
        2/9/26     → 2026-02-09  (2-digit year: 00-68 → 2000-2068, 69-99 → 1969-1999)

    Returns (iso_string, error_or_None).
    """
    import datetime

    v = str(value).strip() if value else ""
    if not v or v.lower() in ("nan", "none", "nat", "n/a", ""):
        return ("", None)

    # Strip Excel datetime timestamp suffix (e.g. "2022-10-17 00:00:00" → "2022-10-17")
    if " " in v:
        v = v.split(" ")[0].strip()

    # ── Slash-separated: MM/DD/YYYY or MM/DD/YY ─────────────────────────────
    if "/" in v:
        parts = v.split("/")
        if len(parts) != 3:
            return ("", f"Row {row_num}, {field}: '{v}' is not a valid date.")
        try:
            month, day = int(parts[0]), int(parts[1])
            yr_raw = parts[2].strip()
            if len(yr_raw) == 2:
                # 2-digit year: mirror Python's strptime %y behaviour
                yr = 2000 + int(yr_raw) if int(yr_raw) < 69 else 1900 + int(yr_raw)
            else:
                yr = int(yr_raw)
            dt = datetime.date(yr, month, day)
            return (dt.isoformat(), None)
        except (ValueError, TypeError):
            return ("", f"Row {row_num}, {field}: '{v}' is not a valid date.")

    # ── Dash-separated: YYYY-MM-DD or MM-DD-YYYY ────────────────────────────
    if "-" not in v:
        return ("", f"Row {row_num}, {field}: '{v}' is not a valid date. Use YYYY-MM-DD, MM-DD-YYYY, or MM/DD/YYYY.")

    parts = v.split("-")
    if len(parts) != 3:
        return ("", f"Row {row_num}, {field}: '{v}' is not a valid date.")

    try:
        first = int(parts[0])
        if first <= 12:                          # MM-DD-YYYY
            month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
        else:                                    # YYYY-MM-DD
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        dt = datetime.date(year, month, day)
        return (dt.isoformat(), None)
    except (ValueError, TypeError):
        return ("", f"Row {row_num}, {field}: '{v}' is not a valid date.")


def _parse_state_column(value: str, csv_city: str, row_num: int) -> tuple[str, list[str], str | None]:
    """Parse the State column into (city, states_list, error_or_None).

    Valid formats
    ─────────────
    'GA'            → city=csv_city,  states=["GA"]
    'GA, AL, SC'    → city=csv_city,  states=["GA","AL","SC"]
    'Atlanta, GA'   → city="Atlanta", states=["GA"]
    '' / 'N/A'      → city=csv_city,  states=[]

    Rejected formats
    ────────────────
    slash/dash separators between codes ('GA/AL', 'GA-AL')
    full state names ('Montana', 'Georgia')
    multiple cities  ('Arlington, SC, Atlanta, GA')
    """
    v = str(value).strip() if value else ""
    if not v or v.lower() in ("nan", "none", "n/a", ""):
        return (csv_city, [], None)

    # Reject slash separator
    if "/" in v:
        return ("", [], f"Row {row_num}, State: '{v}' is invalid. Use comma-separated abbreviations (e.g. 'GA, SC'), not '/'.")

    # Reject dash separator between codes (e.g. 'GA-AL')
    # A lone date-like string in the state column is invalid anyway.
    if "-" in v and "," not in v:
        return ("", [], f"Row {row_num}, State: '{v}' is invalid. Use comma-separated abbreviations (e.g. 'GA, SC'), not '-'.")

    parts = [p.strip() for p in v.split(",") if p.strip()]
    if not parts:
        return (csv_city, [], None)

    city      = csv_city
    states    = []
    city_seen = 0

    for idx, part in enumerate(parts):
        upper = part.upper()
        if upper in STATES:
            states.append(upper)
        else:
            # Non-state token — must be a city and must appear first
            city_seen += 1
            if city_seen > 1:
                return ("", [], f"Row {row_num}, State: '{v}' is invalid. Multiple non-state values detected. Format must be 'City, ST' or 'ST, ST'.")
            if idx != 0:
                return ("", [], f"Row {row_num}, State: '{v}' is invalid. City must come before state abbreviations.")
            if len(part) > 3 or " " in part:
                city = part          # looks like a city name
            else:
                # Short token, not a state — probably a full name abbreviation attempt
                return ("", [], f"Row {row_num}, State: '{part}' is not a recognised state code. Use 2-letter abbreviations (e.g. 'GA').")

    if city_seen == 1 and not states:
        # Had a city-like token but no valid state codes
        return ("", [], f"Row {row_num}, State: No valid state abbreviations found in '{v}'.")

    return (city, states, None)


def _parse_number(value: str, row_num: int, field: str) -> tuple[int, str | None]:
    """Parse a numeric field into a non-negative integer. Returns (int, error_or_None)."""
    v = str(value).strip().replace(",", "").replace("$", "") if value else ""
    if not v or v.lower() in ("nan", "none", ""):
        return (0, None)
    try:
        f = float(v)
    except ValueError:
        return (0, f"Row {row_num}, {field}: '{value}' is not a valid number.")
    if f < 0:
        return (0, f"Row {row_num}, {field}: '{value}' is negative. Must be positive.")
    return (round(f), None)


def _match_enum(value: str, options: list[str]) -> str | None:
    """Case-insensitive match against a list; returns canonical value or None."""
    v = str(value).strip() if value else ""
    if not v or v.lower() in ("nan", "none", ""):
        return ""
    return next((o for o in options if o.lower() == v.lower()), None)


# ---------------------------------------------------------------------------
# Public API — two-step: validate first, insert separately
# ---------------------------------------------------------------------------

def get_excel_sheet_names(csv_file_bytes: bytes) -> list[str]:
    """Return the sheet names from an Excel file. Returns [] on failure."""
    try:
        xl = pd.ExcelFile(BytesIO(csv_file_bytes))
        return xl.sheet_names
    except Exception:
        return []


def validate_csv(csv_file_bytes: bytes, filename: str = "",
                 excel_header_row: int = 1, excel_usecols: str = "",
                 excel_sheet: str | int = 0) -> dict:
    """Validate a CSV/Excel file without writing anything to the database.

    Args:
        csv_file_bytes:   Raw file bytes.
        filename:         Original filename (used to detect .xlsx/.xls vs .csv).
        excel_header_row: 1-based row number of the header row (Excel only). Default 1.
        excel_usecols:    Optional column range string e.g. 'B:S' (Excel only).
        excel_sheet:      Sheet name or 0-based index (Excel only). Default 0 (first sheet).

    Returns:
        {
            "success":       bool,
            "to_insert":     list[dict],
            "skipped_names": list[str],
            "errors":        list[str],
        }
    """
    return _run(csv_file_bytes, filename, dry_run=True,
                excel_header_row=excel_header_row, excel_usecols=excel_usecols,
                excel_sheet=excel_sheet)


def insert_validated_rows(to_insert: list[dict]) -> dict:
    """Insert pre-validated rows returned by validate_csv().

    Returns:
        {"success": bool, "added": int, "error": str}
    """
    if not to_insert:
        return {"success": True, "added": 0, "error": ""}
    try:
        col = get_mongo_client()[_DB_NAME][_COL_NAME]
        col.insert_many(to_insert)
        return {"success": True, "added": len(to_insert), "error": ""}
    except Exception as e:
        return {"success": False, "added": 0, "error": str(e)}


def validate_and_import_csv(csv_file_bytes: bytes, filename: str = "") -> dict:
    """Combined validate + import (kept for backward compatibility)."""
    return _run(csv_file_bytes, filename, dry_run=False)


def _run(csv_file_bytes: bytes, filename: str, dry_run: bool,
         excel_header_row: int = 1, excel_usecols: str = "",
         excel_sheet: str | int = 0) -> dict:
    """Internal implementation shared by validate_csv and validate_and_import_csv."""
    errors: list[str] = []

    # ── Parse file ──────────────────────────────────────────────────────────
    try:
        buf = BytesIO(csv_file_bytes)
        if filename.lower().endswith((".xlsx", ".xls")):
            kwargs: dict = {
                "dtype":           str,
                "keep_default_na": False,
                "header":          max(0, excel_header_row - 1),
                "sheet_name":      excel_sheet,
            }
            if excel_usecols and excel_usecols.strip():
                kwargs["usecols"] = excel_usecols.strip()
            df = pd.read_excel(buf, **kwargs)
        else:
            df = pd.read_csv(buf, dtype=str, keep_default_na=False)
    except Exception as e:
        return _fail([f"Failed to parse file: {e}"])

    # Coerce all column names to strings (NaN column headers become "nan")
    df.columns = [str(c) for c in df.columns]
    df = df.fillna("").astype(str)

    # ── Column check ────────────────────────────────────────────────────────
    # Case-insensitive column normalisation — skip empty/nan column names
    col_map = {c.strip().lower(): c.strip() for c in df.columns
               if c.strip() and c.strip().lower() != "nan"}
    rename  = {col_map[req.lower()]: req for req in _REQUIRED_COLUMNS if req.lower() in col_map}
    df.rename(columns=rename, inplace=True)

    missing = [c for c in _REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        detected = [c for c in df.columns if c not in ("nan", "") and not c.startswith("Unnamed")]
        detected_str = ", ".join(detected) if detected else "(none recognised)"
        return _fail([
            f"Missing required columns: {', '.join(missing)}",
            f"Columns detected in file: {detected_str}",
            "Ensure the file has the correct headers and that the header row / column range settings point to them.",
        ])

    # ── Load DB state ────────────────────────────────────────────────────────
    existing_deals = get_all_deals()
    existing_names = {d["deal_name"].strip().lower() for d in existing_deals if d.get("deal_name")}
    existing_ids   = {d["id"] for d in existing_deals}

    # ── Validate every row ───────────────────────────────────────────────────
    csv_id_rows: dict[int, list[int]] = {}   # csv_id → [row numbers]
    validated:   list[dict]           = []

    for i, row in df.iterrows():
        row_num = int(i) + 2     # human row number (1=header, so data starts at 2)

        # 1. ID
        id_raw = str(row["#"]).strip()
        id_val: int | None = None
        if id_raw and id_raw.lower() not in ("nan", ""):
            try:
                id_val = int(float(id_raw))
                if id_val <= 0:
                    errors.append(f"Row {row_num}, #: '{id_raw}' must be a positive integer.")
                    id_val = None
            except ValueError:
                errors.append(f"Row {row_num}, #: '{id_raw}' is not a valid integer.")
        if id_val is not None:
            csv_id_rows.setdefault(id_val, []).append(row_num)

        # 2. Deal Name
        deal_name = str(row["Deal Name"]).strip()
        if not deal_name or deal_name.lower() == "nan":
            errors.append(f"Row {row_num}, Deal Name: cannot be empty.")
            deal_name = ""

        # 3. Dates
        date_received, err = _parse_date(row["Date Received"], row_num, "Date Received")
        if err: errors.append(err)

        date_closed, err = _parse_date(row["Date Closed"], row_num, "Date Closed")
        if err: errors.append(err)

        # 4. State (may also supply city)
        csv_city  = str(row["City"]).strip()
        city, parsed_states, err = _parse_state_column(str(row["State"]), csv_city, row_num)
        if err: errors.append(err)

        # 5. Numbers
        fi_val, err = _parse_number(row["Fund Investment Amount"], row_num, "Fund Investment Amount")
        if err: errors.append(err)

        ds_val, err = _parse_number(row["Deal Size"], row_num, "Deal Size")
        if err: errors.append(err)

        # 6. Development
        dev_match = _match_enum(row["Development"], ["Yes", "No"])
        if dev_match is None:
            errors.append(f"Row {row_num}, Development: '{row['Development']}' is invalid. Must be 'Yes' or 'No'.")
        dev_val = dev_match if dev_match is not None else ""

        # 7. Stage
        stage_match = _match_enum(row["Stage"], STAGES)
        if stage_match is None:
            errors.append(f"Row {row_num}, Stage: '{row['Stage']}' is invalid. Must be one of: {', '.join(STAGES)}.")
        stage_val = stage_match if stage_match is not None else ""

        # 8. Status
        status_match = _match_enum(row["Status"], STATUSES)
        if status_match is None:
            errors.append(f"Row {row_num}, Status: '{row['Status']}' is invalid. Must be 'Active' or 'Inactive'.")
        status_val = status_match if status_match is not None else ""

        # Free-text fields — accept as-is
        validated.append({
            "id":                     id_val,
            "date_received":          date_received,
            "deal_name":              deal_name,
            "city":                   city,
            "states":                 parsed_states,
            "zip_code":               str(row["Zip Code"]).strip(),
            "tcm_originator":         str(row["TCM Originator"]).strip(),
            "broker":                 str(row["Broker"]).strip(),
            "brokerage_company":      str(row["Brokerage Company"]).strip(),
            "fund_investment_amount": fi_val,
            "deal_size":              ds_val,
            "deal_type":              str(row["Deal Type"]).strip(),
            "deal_subtype":           str(row["Deal Subtype"]).strip(),
            "asset_class":            str(row["Asset Class"]).strip(),
            "development":            dev_val,
            "stage":                  stage_val,
            "status":                 status_val,
            "date_closed":            date_closed,
        })

    # ── Duplicate # within CSV ───────────────────────────────────────────────
    for id_val, rows in csv_id_rows.items():
        if len(rows) > 1:
            errors.append(
                f"Rows {' and '.join(map(str, rows))} both have # value {id_val}. "
                "Duplicate IDs not allowed."
            )

    # ── Abort on any error ───────────────────────────────────────────────────
    if errors:
        return _fail(errors)

    # ── Separate inserts from skipped duplicates ─────────────────────────────
    to_insert:     list[dict] = []
    skipped_names: list[str]  = []
    next_id = (max(existing_ids) + 1) if existing_ids else 1

    for row_dict in validated:
        if row_dict["deal_name"].strip().lower() in existing_names:
            skipped_names.append(row_dict["deal_name"])
            continue

        # Resolve ID collision with DB
        csv_id = row_dict["id"]
        if csv_id is None or csv_id in existing_ids:
            while next_id in existing_ids:
                next_id += 1
            row_dict["id"] = next_id
            existing_ids.add(next_id)
            next_id += 1
        else:
            existing_ids.add(csv_id)

        to_insert.append(row_dict)

    # ── Insert (skipped in dry_run / validate-only mode) ────────────────────
    if not dry_run and to_insert:
        try:
            col = get_mongo_client()[_DB_NAME][_COL_NAME]
            col.insert_many(to_insert)
        except Exception as e:
            return _fail([f"Database insert failed: {e}"])

    return {
        "success":       True,
        "to_insert":     to_insert,        # populated in both modes
        "skipped_names": skipped_names,
        "added":         len(to_insert) if not dry_run else 0,
        "skipped":       len(skipped_names),
        "duplicates":    skipped_names,
        "errors":        [],
    }


def _fail(errors: list[str]) -> dict:
    return {"success": False, "added": 0, "skipped": 0, "duplicates": [], "errors": errors}
