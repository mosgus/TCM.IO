import datetime
import streamlit as st
import pandas as pd

# ❗ ignore unresolved references — Streamlit adds main/ to sys.path
from db.mongo import (
    init_deals_collection, get_all_deals, update_deal,
    STAGES, STATUSES, DEVELOPMENTS, US_STATES,
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

    # TCM Originator Filter
    originator_options = sorted({d.get("tcm_originator", "") for d in all_deals if d.get("tcm_originator")})
    originator_filter = st.multiselect("TCM Originator", originator_options)

    # Brokerage Filter — Broker cascades from Brokerage Company
    brok_col1, brok_col2 = st.columns(2)
    brokerage_filter = brok_col1.multiselect("Brokerage Co.",
        sorted({d.get("brokerage_company", "") for d in all_deals if d.get("brokerage_company")}))
    broker_pool = [d for d in all_deals if not brokerage_filter or d.get("brokerage_company") in brokerage_filter]
    broker_filter = brok_col2.multiselect("Broker",
        sorted({d.get("broker", "") for d in broker_pool if d.get("broker")}))

    # Location Filter — cascading: each field narrows the next
    st.markdown('<p style="font-size:0.875rem; margin-bottom:0;">Location</p>', unsafe_allow_html=True)
    st.caption("State")
    state_filter = st.multiselect("State",
        sorted({d.get("state", "") for d in all_deals if d.get("state")}),
        label_visibility="collapsed")

    # City options limited to states already selected (if any)
    city_pool = [d for d in all_deals if not state_filter or d.get("state") in state_filter]
    city_col, zip_col = st.columns(2)
    with city_col:
        st.caption("City")
        city_filter = st.multiselect("City",
            sorted({d.get("city", "") for d in city_pool if d.get("city")}),
            label_visibility="collapsed")

    # Zip options limited to states + cities already selected (if any)
    zip_pool = [d for d in city_pool if not city_filter or d.get("city") in city_filter]
    with zip_col:
        st.caption("Zip Code")
        zip_filter = st.multiselect("Zip Code",
            sorted({d.get("zip_code", "") for d in zip_pool if d.get("zip_code")}),
            label_visibility="collapsed")

    # Stage Filter
    stage_options = sorted({d.get("stage", "") for d in all_deals if d.get("stage")})
    stage_filter = st.multiselect("Stage", stage_options)

    # Status Filter
    status_options = ["All"] + sorted({d.get("status", "") for d in all_deals if d.get("status")})
    status_filter = st.selectbox("Status", status_options)

    # Date Received Filter
    st.markdown('<p style="font-size:0.875rem; margin-bottom:0;">Date Received</p>', unsafe_allow_html=True)
    dr_col1, dr_col2 = st.columns(2)
    dr_col1.caption("From")
    dr_col2.caption("To")
    date_from = dr_col1.date_input("From", value=None, label_visibility="collapsed", min_value=datetime.date(2000, 1, 1))
    date_to   = dr_col2.date_input("To",   value=None, label_visibility="collapsed", min_value=datetime.date(2000, 1, 1))

    # Date Closed Filter
    st.markdown('<p style="font-size:0.875rem; margin-bottom:0;">Date Closed</p>', unsafe_allow_html=True)
    dc_col1, dc_col2 = st.columns(2)
    dc_col1.caption("From")
    dc_col2.caption("To")
    closed_from = dc_col1.date_input("Closed From", value=None, label_visibility="collapsed", min_value=datetime.date(2000, 1, 1))
    closed_to   = dc_col2.date_input("Closed To",   value=None, label_visibility="collapsed", min_value=datetime.date(2000, 1, 1))
    st.divider()

filters = {}
if originator_filter:        filters["tcm_originator"]    = {"$in": originator_filter}
if brokerage_filter:         filters["brokerage_company"] = {"$in": brokerage_filter}
if broker_filter:            filters["broker"]            = {"$in": broker_filter}
if city_filter:              filters["city"]     = {"$in": city_filter}
if state_filter:             filters["state"]    = {"$in": state_filter}
if zip_filter:               filters["zip_code"] = {"$in": zip_filter}
if stage_filter:             filters["stage"]          = {"$in": stage_filter}
if status_filter != "All":   filters["status"]         = status_filter
if date_from or date_to:
    date_filter = {}
    if date_from: date_filter["$gte"] = date_from.isoformat()
    if date_to:   date_filter["$lte"] = date_to.isoformat()
    filters["date_received"] = date_filter
if closed_from or closed_to:
    closed_filter = {}
    if closed_from: closed_filter["$gte"] = closed_from.isoformat()
    if closed_to:   closed_filter["$lte"] = closed_to.isoformat()
    filters["date_closed"] = closed_filter

deals = get_all_deals(filters) if filters else all_deals

# --- Deals Table ---
st.subheader("Deals")
if deals:
    df = pd.DataFrame(deals).rename(columns=_COL_LABELS)
    st.dataframe(df, width='stretch', hide_index=True)
else:
    st.info("No deals match the current filters.")

if "expander_key" not in st.session_state:
    st.session_state.expander_key = 0

if st.button("↺ Refresh"):
    st.session_state.expander_key += 1
    st.rerun()

# --- Edit Form ---
st.divider()

with st.expander("Edit Deal ✎", expanded=False, key=f"edit_expander_{st.session_state.expander_key}"):
    if not deals:
        st.warning("No deals match the current filters." if filters else "No deals available to edit.")
    else:
        deal_lookup = {d["deal_name"]: d for d in deals}

        deal_options = list(deal_lookup.keys())
        # Reset stored selection if it no longer exists in the current options
        if st.session_state.get("selected_deal") not in deal_options:
            st.session_state["selected_deal"] = deal_options[0]
        selected_name = st.selectbox("Deal", options=deal_options, key="selected_deal")
        s = deal_lookup[selected_name]

        with st.form("edit_deal_form"):

            deal_name = st.text_input("Deal Name", value=s.get("deal_name", ""), placeholder="ex: Peachtree Corners NPL")

            c1, c2 = st.columns(2)
            date_received = c1.date_input("Date Received", value=_to_date(s.get("date_received", "")), format="YYYY-MM-DD", min_value=datetime.date(2016, 1, 1))
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
