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
US_STATES = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY"
]

_SEED_DEALS = [
    {
        "id": 1,
        "date_received": "2025-01-10",
        "deal_name": "Peachtree Industrial Park",
        "city": "Atlanta",          "state": "GA",  "zip_code": "30318",
        "tcm_originator": "Gus",
        "broker": "John Smith",     "brokerage_company": "CBRE",
        "fund_investment_amount": 2500000.0,  "deal_size": 12000000.0,
        "deal_type": "Debt",        "deal_subtype": "First Lien",
        "asset_class": "Industrial","development": "Stabilized",
        "stage": "Initial Review",  "status": "Active",
        "date_closed": "",
    },
    {
        "id": 2,
        "date_received": "2025-02-03",
        "deal_name": "Riverside Office Complex",
        "city": "Savannah",         "state": "GA",  "zip_code": "31401",
        "tcm_originator": "G. Balch",
        "broker": "Sarah Lee",      "brokerage_company": "JLL",
        "fund_investment_amount": 5000000.0,  "deal_size": 22000000.0,
        "deal_type": "Equity",      "deal_subtype": "Preferred Equity",
        "asset_class": "Office",    "development": "Value-Add",
        "stage": "Term Sheet Out",  "status": "Active",
        "date_closed": "",
    },
    {
        "id": 3,
        "date_received": "2024-11-20",
        "deal_name": "Midtown Retail Strip",
        "city": "Atlanta",          "state": "GA",  "zip_code": "30309",
        "tcm_originator": "G. Balch",
        "broker": "Mike Torres",    "brokerage_company": "Colliers",
        "fund_investment_amount": 1200000.0,  "deal_size": 6000000.0,
        "deal_type": "Debt",        "deal_subtype": "Second Lien",
        "asset_class": "Retail",    "development": "Stabilized",
        "stage": "Closed",          "status": "Inactive",
        "date_closed": "2025-01-05",
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

    Args:
        deal_id: Integer id of the target deal.
        **kwargs: Field/value pairs to update, e.g. stage="Closed", city="Macon".

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
