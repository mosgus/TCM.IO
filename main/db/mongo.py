"""
MongoDB connection and CRUD layer for TCM.io.

Credential resolution order:
  1. keys/mongo.txt  — local dev (line 3 = full URI)
  2. st.secrets["MONGO_URI"] — Streamlit Cloud deployment
"""

import streamlit as st
from pymongo import MongoClient
from pymongo.server_api import ServerApi

_DB_NAME  = "toccoaIO_db"
_COL_NAME = "deal_pipeline"

# --- Dropdown option lists ---
STAGES      = ["Initial Review", "Closing", "Full Underwriting Memo", "Term Sheet Out", "Term Sheet Signed", "Possible Future Opportunity"]
STATUSES    = ["Active", "Inactive"]
DEAL_TYPES  = ["Equity", "Debt", "NPL", "Hybrid", "Other"]
DEAL_SUBTYPES  = ["Co-GP", "Construction Loan", "JV Equity", "Second Lien", "Preferred Equity", "Common Equity", "Other"]
ASSET_CLASSES  = ["Multifamily", "Office", "Retail", "Industrial", "Hospitality", "Mixed-Use", "Land", "Healthcare", "Self-Storage", "Other"]
DEVELOPMENTS   = ["Yes", "No"]
STATES = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY", # All US States
    "DC",  # District of Columbia
    "USA", "CAN", "MEX", "SA", "EU", "CN", "N/A"  # potential regions/nation-states
]


def parse_state_input(state_str: str) -> list[str]:
    """Parse comma or space-separated state abbreviations and validate against STATES.

    Args:
        state_str: e.g. "NC, SC, FL" or "NC,SC,FL" or "NC"

    Returns:
        List of valid 2-letter state codes, e.g. ["NC", "SC", "FL"].
        Returns empty list if input is blank or no valid states found.
    """
    if not state_str or not state_str.strip():
        return []
    parts = [s.strip().upper() for s in state_str.replace(",", " ").split() if s.strip()]
    return [s for s in parts if s in STATES]


# default for empty DB — states stored as arrays
_SEED_DEALS = [
    {
        "id": 1,
        "date_received": "2025-01-10",
        "deal_name": "Midwood Rosswell",
        "city": "Roswell",          "states": ["GA"],  "zip_code": "30075",
        "tcm_originator": "Barron Garbo",
        "broker": "Tyler Hogan",     "brokerage_company": "Capstone",
        "fund_investment_amount": 0,  "deal_size":  6200000,
        "deal_type": "Equity",        "deal_subtype": "Principal Investment",
        "asset_class": "Multifamily","development": "No",
        "stage": "Term Sheet Out",  "status": "Inactive",
        "date_closed": "",
    }
]


@st.cache_resource
def get_mongo_client() -> MongoClient:
    """Return a cached MongoClient.

    Tries keys/mongo.txt first (local dev — full URI on line 3).
    Falls back to st.secrets['MONGO_URI'] on Streamlit Cloud.
    """
    try:
        with open("keys/mongo.txt", "r") as f:
            lines = f.read().splitlines()
        uri = lines[2]
    except FileNotFoundError:
        uri = st.secrets["MONGO_URI"]
    return MongoClient(uri, server_api=ServerApi('1'))


def init_deals_collection() -> None:
    """Ensure the deals collection exists. Creates and seeds it only if absent."""
    try:
        db = get_mongo_client()[_DB_NAME]
        if _COL_NAME not in db.list_collection_names():
            db[_COL_NAME].insert_many(_SEED_DEALS)
    except Exception as e:
        st.error(f"Failed to initialise deals collection: {e}")


def get_all_deals(filters: dict = None) -> list[dict]:
    """Return all deal documents sorted by id, optionally filtered.

    Args:
        filters: MongoDB query dict e.g. {"stage": "Closed"}.

    Returns:
        List of deal dicts with MongoDB _id excluded.
    """
    try:
        col = get_mongo_client()[_DB_NAME][_COL_NAME]
        return list(col.find(filters or {}, {"_id": 0}).sort("id", 1))
    except Exception as e:
        st.error(f"Failed to fetch deals: {e}")
        return []


def add_deal(**kwargs) -> bool:
    """Insert a new deal document, auto-incrementing the id field.
    Pass states as a list: states=["NC", "SC"].

    Returns:
        True on success, False otherwise.
    """
    try:
        col = get_mongo_client()[_DB_NAME][_COL_NAME]
        last = col.find_one(sort=[("id", -1)])
        kwargs["id"] = (last["id"] + 1) if last else 1
        col.insert_one(kwargs)
        return True
    except Exception as e:
        st.error(f"Failed to add deal: {e}")
        return False


def delete_deals_by_range(min_id: int, max_id: int) -> int:
    """Delete all deals whose id is between min_id and max_id (inclusive).

    Returns the number of documents deleted.
    """
    try:
        col = get_mongo_client()[_DB_NAME][_COL_NAME]
        result = col.delete_many({"id": {"$gte": min_id, "$lte": max_id}})
        return result.deleted_count
    except Exception as e:
        st.error(f"Failed to bulk delete deals: {e}")
        return 0


def delete_deal(deal_id: int) -> bool:
    """Permanently delete a deal document by id.

    Returns:
        True if a document was deleted, False otherwise.
    """
    try:
        col = get_mongo_client()[_DB_NAME][_COL_NAME]
        result = col.delete_one({"id": deal_id})
        return result.deleted_count > 0
    except Exception as e:
        st.error(f"Failed to delete deal {deal_id}: {e}")
        return False


def update_deal(deal_id: int, **kwargs) -> bool:
    """Update a deal by id with any provided fields via $set.
    Pass states as a list: states=["NC", "SC"].

    Args:
        deal_id: Integer id of the target deal.
        **kwargs: Field/value pairs to update.

    Returns:
        True if a document was matched, False otherwise.
    """
    if not kwargs:
        return False
    try:
        col = get_mongo_client()[_DB_NAME][_COL_NAME]
        result = col.update_one({"id": deal_id}, {"$set": kwargs})
        return result.matched_count > 0
    except Exception as e:
        st.error(f"Failed to update deal {deal_id}: {e}")
        return False
