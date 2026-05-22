import datetime
import streamlit as st
import pandas as pd

# ❗ ignore unresolved references — Streamlit adds main/ to sys.path
from db.mongo import (
    init_deals_collection, get_all_deals, update_deal,
    STAGES, STATUSES, DEAL_TYPES, DEAL_SUBTYPES,
    ASSET_CLASSES, DEVELOPMENTS, US_STATES,
)

# Human-readable column labels for the dataframe display
_COL_LABELS = {
    "id":                     "#",
    "date_received":          "Date Received",
    "deal_name":              "Deal Name",
    "city":                   "City", # Extra Column
    "state":                  "State",
    "zip_code":               "Zip Code",
    "tcm_originator":         "TCM Originator",
    "broker":                 "Broker",
    "brokerage_company":      "Brokerage Company",
    "fund_investment_amount": "Fund Investment Amount",
    "deal_size":              "Deal Size",
    "deal_type":              "Deal Type",
    "deal_subtype":           "Deal Subtype",
    "asset_class":            "Asset Class",
    "development":            "Development",
    "stage":                  "Stage",
    "status":                 "Status",
    "date_closed":            "Date Closed",
}


def _to_date(value: str) -> datetime.date:
    """Parse a stored YYYY-MM-DD string to datetime.date; fall back to today."""
    try:
        return datetime.date.fromisoformat(value) if value else datetime.date.today()
    except ValueError:
        return datetime.date.today()



def _selectbox_index(options: list, value: str) -> int:
    """Return the index of value in options, or 0 if not found."""
    return options.index(value) if value in options else 0


# -----------------------------------------------------------------------

init_deals_collection()

st.title("Business Development")
st.caption("Deal pipeline")
st.markdown(
    """
    <style>
    button[kind="primary"],
    button[data-testid="baseButton-primary"],
    div[data-testid="stFormSubmitButton"] button {
        background-color: #16a34a !important;
        border-color: #74b37a !important;
        color: white !important;
    }

    button[kind="primary"]:hover,
    button[data-testid="baseButton-primary"]:hover,
    div[data-testid="stFormSubmitButton"] button:hover {
        background-color: #15803d !important;
        border-color: #15803d !important;
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
) # Sets color of save button 🟢

# --- Sidebar: filters + refresh ---
with st.sidebar:
    st.subheader("Filters")
    all_deals = get_all_deals()
    stage_options  = ["All"] + sorted({d.get("stage",  "") for d in all_deals})
    status_options = ["All"] + sorted({d.get("status", "") for d in all_deals})
    stage_filter  = st.selectbox("Stage",  stage_options)
    status_filter = st.selectbox("Status", status_options)
    st.divider()

filters = {}
if stage_filter  != "All": filters["stage"]  = stage_filter
if status_filter != "All": filters["status"] = status_filter

deals = get_all_deals(filters) if filters else all_deals

# --- Deals Table ---
st.subheader("Deals")
if deals:
    df = pd.DataFrame(deals).rename(columns=_COL_LABELS)
    st.dataframe(df, width='stretch', hide_index=True)
else:
    st.info("No deals match the current filters.")

if st.button("↺ Refresh"):
    st.rerun()
# --- Deals Table ---

# --- Edit Form ---
st.divider()

with st.expander("Edit Deal", expanded=False):
    if not all_deals:
        st.warning("No deals available to edit.")
    else:
        deal_lookup = {d["deal_name"]: d for d in all_deals}

        selected_name = st.selectbox("Deal", options=list(deal_lookup.keys()))
        s = deal_lookup[selected_name]

        with st.form("edit_deal_form"):

            deal_name = st.text_input("Deal Name", value=s.get("deal_name", ""), placeholder="ex: Peachtree Corners NPL")

            c1, c2 = st.columns(2)
            date_received = c1.date_input("Date Received", value=_to_date(s.get("date_received", "")), format="YYYY-MM-DD")
            date_closed   = c2.text_input("Date Closed (YYYY-MM-DD)", value=s.get("date_closed", ""), placeholder="Leave blank if not closed")

            c1, c2, c3 = st.columns([3, 1, 1])
            city     = c1.text_input("City",     value=s.get("city",     ""))
            state    = c2.selectbox("State",     US_STATES, index=_selectbox_index(US_STATES, s.get("state", "GA")))
            zip_code = c3.text_input("Zip Code", value=s.get("zip_code", ""))

            c1, c2, c3 = st.columns(3)
            tcm_originator    = c1.text_input("TCM Originator",    value=s.get("tcm_originator",    ""))
            broker            = c2.text_input("Broker",            value=s.get("broker",            ""))
            brokerage_company = c3.text_input("Brokerage Company", value=s.get("brokerage_company", ""))

            c1, c2 = st.columns(2)
            fund_investment_amount = c1.number_input("Fund Investment Amount ($)", min_value=0.0, step=10000.0, value=float(s.get("fund_investment_amount", 0)))
            deal_size              = c2.number_input("Deal Size ($)",              min_value=0.0, step=10000.0, value=float(s.get("deal_size", 0)))

            c1, c2 = st.columns(2)
            deal_type    = c1.text_input("Deal Type",    value=s.get("deal_type",    ""), placeholder="e.g. Debt, Equity, NPL")
            deal_subtype = c2.text_input("Deal Subtype", value=s.get("deal_subtype", ""), placeholder="e.g. Co-GP, First Lien, Mezz")

            c1, c2 = st.columns([3, 1])
            asset_class = c1.text_input("Asset Class", value=s.get("asset_class", ""), placeholder="e.g. Retail, Multifamily, Industrial")
            development = c2.selectbox("Development",  DEVELOPMENTS, index=_selectbox_index(DEVELOPMENTS, s.get("development", "")))

            c1, c2 = st.columns(2)
            stage  = c1.selectbox("Stage",  STAGES,   index=_selectbox_index(STAGES,   s.get("stage",  "")))
            status = c2.selectbox("Status", STATUSES, index=_selectbox_index(STATUSES, s.get("status", "")))

            _, mid, _ = st.columns([1, 0.75, 1])
            submitted = mid.form_submit_button("Save ✔", type="primary", width="stretch")

        if submitted:
            updated = update_deal(
                s["id"],
                deal_name              = deal_name,
                date_received          = date_received.isoformat(),
                date_closed            = date_closed.strip(),
                city                   = city,
                state                  = state,
                zip_code               = zip_code,
                tcm_originator         = tcm_originator,
                broker                 = broker,
                brokerage_company      = brokerage_company,
                fund_investment_amount = fund_investment_amount,
                deal_size              = deal_size,
                deal_type              = deal_type,
                deal_subtype           = deal_subtype,
                asset_class            = asset_class,
                development            = development,
                stage                  = stage,
                status                 = status,
            )
            if updated:
                st.success(f"'{selected_name}' saved. ↺ Refresh to see changes.")
            else:
                st.error(f"No deal found with id {s['id']}.")
