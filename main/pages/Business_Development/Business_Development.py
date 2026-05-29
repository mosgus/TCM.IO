import datetime
import streamlit as st
import pandas as pd

# ❗ ignore unresolved references — Streamlit adds main/ to sys.path
from db.mongo import (
    init_deals_collection, get_all_deals, update_deal, delete_deal, add_deal,
    delete_deals_by_range,
    STAGES, STATUSES, DEVELOPMENTS, STATES,
)
from db.csv_importer import validate_csv, insert_validated_rows, get_excel_sheet_names

# Human-readable column labels for the dataframe display
_COL_LABELS = {
    "id":                     "#",
    "date_received":          "Date Received",
    "deal_name":              "Deal Name",
    "city":                   "City", # Extra Column
    "states":                 "State(s)/Region",
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
st.caption("Edit, Delete, Add-to, & Filter the Deal pipeline")

st.markdown(
    """
    <style>
    /* Save — green: all form submit buttons (Save is the only one) */
    div[data-testid="stFormSubmitButton"] button {
        background-color: #16a34a !important;
        border-color: #74b37a !important;
        color: white !important;
    }
    div[data-testid="stFormSubmitButton"] button:hover {
        background-color: #15803d !important;
        border-color: #15803d !important;
        color: white !important;
    }

    /* Delete & Yes delete — red: regular primary buttons (not form submit) */
    button[data-testid="baseButton-primary"] {
        background-color: #dc2626 !important;
        border-color: #dc2626 !important;
        color: white !important;
    }
    button[data-testid="baseButton-primary"]:hover {
        background-color: #b91c1c !important;
        border-color: #b91c1c !important;
        color: white !important;
    }

    /* ── Expander accent colours (marker div + :has()) ── */

    /* Filters — yellow */
    [data-testid="stExpander"]:has(.exp-filters) details > summary {
        background-color:rgba(234,179,8,.18) !important;
        border-left:3px solid rgba(234,179,8,.7) !important;
        border-radius:4px !important;
    }
    [data-testid="stExpander"]:has(.exp-filters) details > summary p { color:#fbbf24 !important; }
    [data-testid="stExpander"]:has(.exp-filters) details > summary svg { fill:#fbbf24 !important; }
    [data-testid="stExpander"]:has(.exp-filters) details { border:1px solid rgba(234,179,8,.2) !important; border-radius:6px !important; }
    /* reset nested expanders inside Filters to avoid inheriting yellow */
    [data-testid="stExpander"]:has(.exp-filters) [data-testid="stExpander"] details > summary { background-color:transparent !important; border-left:none !important; }
    [data-testid="stExpander"]:has(.exp-filters) [data-testid="stExpander"] details > summary p { color:inherit !important; }
    [data-testid="stExpander"]:has(.exp-filters) [data-testid="stExpander"] details > summary svg { fill:inherit !important; }
    [data-testid="stExpander"]:has(.exp-filters) [data-testid="stExpander"] details { border:none !important; }

    /* Edit Deal — blue */
    [data-testid="stExpander"]:has(.exp-edit) details > summary {
        background-color:rgba(59,130,246,.18) !important;
        border-left:3px solid rgba(59,130,246,.7) !important;
        border-radius:4px !important;
    }
    [data-testid="stExpander"]:has(.exp-edit) details > summary p { color:#60a5fa !important; }
    [data-testid="stExpander"]:has(.exp-edit) details > summary svg { fill:#60a5fa !important; }
    [data-testid="stExpander"]:has(.exp-edit) details { border:1px solid rgba(59,130,246,.2) !important; border-radius:6px !important; }

    /* Add Deal — green */
    [data-testid="stExpander"]:has(.exp-add) details > summary {
        background-color:rgba(22,163,74,.18) !important;
        border-left:3px solid rgba(22,163,74,.7) !important;
        border-radius:4px !important;
    }
    [data-testid="stExpander"]:has(.exp-add) details > summary p { color:#4ade80 !important; }
    [data-testid="stExpander"]:has(.exp-add) details > summary svg { fill:#4ade80 !important; }
    [data-testid="stExpander"]:has(.exp-add) details { border:1px solid rgba(22,163,74,.2) !important; border-radius:6px !important; }

    /* Delete Deal — red */
    [data-testid="stExpander"]:has(.exp-delete) details > summary {
        background-color:rgba(220,38,38,.18) !important;
        border-left:3px solid rgba(220,38,38,.7) !important;
        border-radius:4px !important;
    }
    [data-testid="stExpander"]:has(.exp-delete) details > summary p { color:#f87171 !important; }
    [data-testid="stExpander"]:has(.exp-delete) details > summary svg { fill:#f87171 !important; }
    [data-testid="stExpander"]:has(.exp-delete) details { border:1px solid rgba(220,38,38,.2) !important; border-radius:6px !important; }
    </style>
    """,
    unsafe_allow_html=True,
) # Sets color of save button 🟢

#--- Deals table ---
all_deals = get_all_deals()

if "filt_v" not in st.session_state:
    st.session_state.filt_v = 0
fv = st.session_state.filt_v

# Reserve the table's visual position — filled after filters are defined
table_container = st.container()

# --- Filters Form ---
with st.expander("Filters", expanded=False, key=f"filters_expander_{fv}"):
    st.markdown('<div class="exp-filters"></div>', unsafe_allow_html=True)

    # Row 1: Deal | Originator/Broker
    row1_c1, row1_c2 = st.columns(2)

    with row1_c1:
        with st.expander("Deal", expanded=False):
            dt_col1, dt_col2 = st.columns(2)
            deal_type_filter    = dt_col1.multiselect("Deal Type",    sorted({d.get("deal_type",    "") for d in all_deals if d.get("deal_type")}),    placeholder=" ", key=f"filt_deal_type_{fv}")
            deal_subtype_filter = dt_col2.multiselect("Deal Subtype", sorted({d.get("deal_subtype", "") for d in all_deals if d.get("deal_subtype")}), placeholder=" ", key=f"filt_deal_subtype_{fv}")
            ac_col1, ac_col2 = st.columns(2)
            asset_class_filter  = ac_col1.multiselect("Asset Class",  sorted({d.get("asset_class",  "") for d in all_deals if d.get("asset_class")}),  placeholder=" ", key=f"filt_asset_class_{fv}")
            development_filter  = ac_col2.multiselect("Development",  sorted({d.get("development",  "") for d in all_deals if d.get("development")}),  placeholder=" ", key=f"filt_development_{fv}")
            st.markdown('<p style="font-size:0.875rem; margin-bottom:0;">Fund Investment ($)</p>', unsafe_allow_html=True)
            fi_col1, fi_col2 = st.columns(2)
            fi_col1.markdown('<p style="font-size:0.75rem; margin-bottom:-0.1rem; color:rgba(250,250,250,0.6);">Min</p>', unsafe_allow_html=True)
            fi_col2.markdown('<p style="font-size:0.75rem; margin-bottom:-0.1rem; color:rgba(250,250,250,0.6);">Max</p>', unsafe_allow_html=True)
            fi_min = fi_col1.number_input("FI Min", value=None, min_value=0, step=10000, label_visibility="collapsed", placeholder="Min", key=f"filt_fi_min_{fv}")
            fi_max = fi_col2.number_input("FI Max", value=None, min_value=0, step=10000, label_visibility="collapsed", placeholder="Max", key=f"filt_fi_max_{fv}")
            st.markdown('<p style="font-size:0.875rem; margin-bottom:0;">Deal Size ($)</p>', unsafe_allow_html=True)
            ds_col1, ds_col2 = st.columns(2)
            ds_col1.markdown('<p style="font-size:0.75rem; margin-bottom:-0.1rem; color:rgba(250,250,250,0.6);">Min</p>', unsafe_allow_html=True)
            ds_col2.markdown('<p style="font-size:0.75rem; margin-bottom:-0.1rem; color:rgba(250,250,250,0.6);">Max</p>', unsafe_allow_html=True)
            ds_min = ds_col1.number_input("DS Min", value=None, min_value=0, step=10000, label_visibility="collapsed", placeholder="Min", key=f"filt_ds_min_{fv}")
            ds_max = ds_col2.number_input("DS Max", value=None, min_value=0, step=10000, label_visibility="collapsed", placeholder="Max", key=f"filt_ds_max_{fv}")

    with row1_c2:
        with st.expander("Originator/Broker", expanded=False):
            originator_options = sorted({d.get("tcm_originator", "") for d in all_deals if d.get("tcm_originator")})
            originator_filter = st.multiselect("TCM Originator", originator_options, placeholder=" ", key=f"filt_originator_{fv}")
            brok_col1, brok_col2 = st.columns(2)
            brokerage_filter  = brok_col1.multiselect("Brokerage Co.", sorted({d.get("brokerage_company", "") for d in all_deals if d.get("brokerage_company")}), placeholder=" ", key=f"filt_brokerage_{fv}")
            broker_pool       = [d for d in all_deals if not brokerage_filter or d.get("brokerage_company") in brokerage_filter]
            broker_filter     = brok_col2.multiselect("Broker",        sorted({d.get("broker", "") for d in broker_pool if d.get("broker")}), placeholder=" ", key=f"filt_broker_{fv}")

    # Row 2: Stage/Status | Location
    row2_c1, row2_c2 = st.columns(2)

    with row2_c1:
        with st.expander("Stage/Status", expanded=False):
            stage_options  = sorted({d.get("stage", "") for d in all_deals if d.get("stage")})
            stage_filter   = st.multiselect("Stage", stage_options, placeholder=" ", key=f"filt_stage_{fv}")
            status_options = ["All"] + sorted({d.get("status", "") for d in all_deals if d.get("status")})
            status_filter  = st.selectbox("Status", status_options, key=f"filt_status_{fv}")

    with row2_c2:
        with st.expander("Location", expanded=False):
            state_filter = st.multiselect("State(s)/Region", sorted({s for d in all_deals for s in d.get("states", []) if s}), placeholder=" ", key=f"filt_state_{fv}")
            city_pool    = [d for d in all_deals if not state_filter or any(s in state_filter for s in d.get("states", []))]
            city_col, zip_col = st.columns(2)
            with city_col:
                city_filter = st.multiselect("City",     sorted({d.get("city",     "") for d in city_pool if d.get("city")}),     placeholder=" ", key=f"filt_city_{fv}")
            zip_pool = [d for d in city_pool if not city_filter or d.get("city") in city_filter]
            with zip_col:
                zip_filter  = st.multiselect("Zip Code", sorted({d.get("zip_code", "") for d in zip_pool if d.get("zip_code")}), placeholder=" ", key=f"filt_zip_{fv}")

    # Row 3: Dates | Reset button
    row3_c1, row3_c2 = st.columns(2)

    with row3_c1:
        with st.expander("Dates", expanded=False):
            st.markdown('<p style="font-size:0.875rem; margin-bottom:0;">Date Received</p>', unsafe_allow_html=True)
            dr_col1, dr_col2 = st.columns(2)
            dr_col1.markdown('<p style="font-size:0.75rem; margin-bottom:-0.1rem; color:rgba(250,250,250,0.6);">From</p>', unsafe_allow_html=True)
            dr_col2.markdown('<p style="font-size:0.75rem; margin-bottom:-0.1rem; color:rgba(250,250,250,0.6);">To</p>',   unsafe_allow_html=True)
            date_from   = dr_col1.date_input("From",        value=None, label_visibility="collapsed", min_value=datetime.date(2015, 1, 1), key=f"filt_date_from_{fv}")
            date_to     = dr_col2.date_input("To",          value=None, label_visibility="collapsed", min_value=datetime.date(2015, 1, 1), key=f"filt_date_to_{fv}")
            st.markdown('<p style="font-size:0.875rem; margin-bottom:0;">Date Closed</p>', unsafe_allow_html=True)
            dc_col1, dc_col2 = st.columns(2)
            dc_col1.markdown('<p style="font-size:0.75rem; margin-bottom:-0.1rem; color:rgba(250,250,250,0.6);">From</p>', unsafe_allow_html=True)
            dc_col2.markdown('<p style="font-size:0.75rem; margin-bottom:-0.1rem; color:rgba(250,250,250,0.6);">To</p>',   unsafe_allow_html=True)
            closed_from = dc_col1.date_input("Closed From", value=None, label_visibility="collapsed", min_value=datetime.date(2015, 1, 1), key=f"filt_closed_from_{fv}")
            closed_to   = dc_col2.date_input("Closed To",   value=None, label_visibility="collapsed", min_value=datetime.date(2015, 1, 1), key=f"filt_closed_to_{fv}")

btn_c1, btn_c2 = st.columns(2)
if btn_c1.button("↩ Reset Filters", width="stretch", key="reset_filters_outer"):
    st.session_state.filt_v += 1
    st.rerun()
if btn_c2.button("↺ Refresh Table", width="stretch"):
    st.session_state.expander_key += 1
    st.rerun()


# Build filters from widget values
filters = {}
if originator_filter:        filters["tcm_originator"]    = {"$in": originator_filter}
if brokerage_filter:         filters["brokerage_company"] = {"$in": brokerage_filter}
if broker_filter:            filters["broker"]            = {"$in": broker_filter}
if city_filter:              filters["city"]     = {"$in": city_filter}
if state_filter:             filters["states"]   = {"$in": state_filter}
if zip_filter:               filters["zip_code"] = {"$in": zip_filter}
if stage_filter:             filters["stage"]        = {"$in": stage_filter}
if deal_type_filter:         filters["deal_type"]    = {"$in": deal_type_filter}
if deal_subtype_filter:      filters["deal_subtype"] = {"$in": deal_subtype_filter}
if asset_class_filter:       filters["asset_class"]  = {"$in": asset_class_filter}
if development_filter:       filters["development"]  = {"$in": development_filter}
if fi_min is not None or fi_max is not None:
    fi_filter = {}
    if fi_min is not None: fi_filter["$gte"] = fi_min
    if fi_max is not None: fi_filter["$lte"] = fi_max
    filters["fund_investment_amount"] = fi_filter
if ds_min is not None or ds_max is not None:
    ds_filter = {}
    if ds_min is not None: ds_filter["$gte"] = ds_min
    if ds_max is not None: ds_filter["$lte"] = ds_max
    filters["deal_size"] = ds_filter
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

# --- Fill table container (renders at top, above the Filters expander) 💻
with table_container:
    st.subheader("Deal Pipeline table")
    if deals:
        df = pd.DataFrame(deals).rename(columns=_COL_LABELS)
        for col in ("Fund Investment Amount", "Deal Size"):
            if col in df.columns:
                df[col] = df[col].apply(lambda x: f"{int(x):,}" if x not in (None, "", 0) else "")
        if "State(s)" in df.columns:
            df["State(s)/Region"] = df["State(s)/Region"].apply(lambda x: ", ".join(x) if isinstance(x, list) else (x or ""))
        st.dataframe(df, width='stretch', hide_index=True)
    else:
        st.info("No deals match the current filters.")

if "expander_key" not in st.session_state:
    st.session_state.expander_key = 0
    
st.divider()
# TODO: visualize segments
'''📊 Visualizations will go here'''
st.divider()

# --- Edit Form ✏️---
with st.expander("Edit Deal ✎", expanded=False, key=f"edit_expander_{st.session_state.expander_key}"):
    st.markdown('<div class="exp-edit"></div>', unsafe_allow_html=True)
    if not deals:
        st.warning("No deals match the current filters." if filters else "No deals available to edit.")
    else:
        deal_lookup = {d["deal_name"]: d for d in deals}

        deal_options = list(deal_lookup.keys())
        # Reset stored selection if it no longer exists in the current options
        if st.session_state.get("selected_deal") not in deal_options:
            st.session_state["selected_deal"] = deal_options[0]
        selected_name = st.selectbox("Select Deal", options=deal_options, key="selected_deal")
        s = deal_lookup[selected_name]

        with st.form("edit_deal_form"):

            deal_name = st.text_input("Deal Name", value=s.get("deal_name", ""), placeholder="ex: Peachtree Corners NPL")

            c1, c2 = st.columns(2)
            date_received = c1.date_input("Date Received", value=_to_date(s.get("date_received", "")), format="YYYY-MM-DD", min_value=datetime.date(2016, 1, 1))
            date_closed   = c2.text_input("Date Closed (YYYY-MM-DD)", value=s.get("date_closed", ""), placeholder="Leave blank if not closed")

            c1, c2, c3 = st.columns([2, 2, 1])
            city     = c1.text_input("City",      value=s.get("city",     ""))
            states   = c2.multiselect("State(s)/Region", STATES, default=[x for x in s.get("states", []) if x in STATES])
            zip_code = c3.text_input("Zip Code",  value=s.get("zip_code", ""))

            c1, c2, c3 = st.columns(3)
            tcm_originator    = c1.text_input("TCM Originator",    value=s.get("tcm_originator",    ""))
            broker            = c2.text_input("Broker",            value=s.get("broker",            ""))
            brokerage_company = c3.text_input("Brokerage Company", value=s.get("brokerage_company", ""))

            c1, c2 = st.columns(2)
            fund_investment_amount = c1.number_input("Fund Investment Amount ($)", min_value=0, step=10000, value=int(s.get("fund_investment_amount", 0) or 0))
            deal_size              = c2.number_input("Deal Size ($)",              min_value=0, step=10000, value=int(s.get("deal_size", 0) or 0))

            c1, c2 = st.columns(2)
            deal_type    = c1.text_input("Deal Type",    value=s.get("deal_type",    ""), placeholder="e.g. Debt, Equity, NPL")
            deal_subtype = c2.text_input("Deal Subtype", value=s.get("deal_subtype", ""), placeholder="e.g. Co-GP, First Lien, Mezz")

            c1, c2 = st.columns([3, 1])
            asset_class = c1.text_input("Asset Class", value=s.get("asset_class", ""), placeholder="e.g. Retail, Multifamily, Industrial")
            development = c2.selectbox("Development",  DEVELOPMENTS, index=_selectbox_index(DEVELOPMENTS, s.get("development", "")))

            c1, c2 = st.columns(2)
            stage  = c1.selectbox("Stage",  STAGES,   index=_selectbox_index(STAGES,   s.get("stage",  "")))
            status = c2.selectbox("Status", STATUSES, index=_selectbox_index(STATUSES, s.get("status", "")))

            _, save_butt, _ = st.columns([1, 0.8, 1])
            submitted = save_butt.form_submit_button("Save ✔", type="primary", width="stretch")

        if submitted:
            other_names = {d["deal_name"].strip().lower() for d in all_deals if d["id"] != s["id"]}
            if not deal_name.strip():
                st.error("Deal Name cannot be empty.")
            elif deal_name.strip().lower() in other_names:
                st.error(f"A deal named '{deal_name.strip()}' already exists. Use a unique name.")
            else:
                updated = update_deal(
                    s["id"],
                    deal_name              = deal_name.strip(),
                    date_received          = date_received.isoformat(),
                    date_closed            = date_closed.strip(),
                    city                   = city,
                    states                 = states,
                    zip_code               = zip_code,
                    tcm_originator         = tcm_originator,
                    broker                 = broker,
                    brokerage_company      = brokerage_company,
                    fund_investment_amount = int(fund_investment_amount),
                    deal_size              = int(deal_size),
                    deal_type              = deal_type,
                    deal_subtype           = deal_subtype,
                    asset_class            = asset_class,
                    development            = development,
                    stage                  = stage,
                    status                 = status,
                )
                if updated:
                    st.success(f"'{deal_name.strip()}' saved. ↺ Refresh to see changes.")
                else:
                    st.error(f"No deal found with id {s['id']}.")

# --- Add Deal ➕---
_BLANK = "Blank (new deal)"

# Bulk Add functionality
@st.dialog("Bulk Add Deals")
def _bulk_add_dialog():
    st.caption("Upload a CSV or Excel file. All rows are validated before anything is inserted — one bad row rejects the whole file.")

    uploaded = st.file_uploader("Choose file", type=["csv", "xlsx", "xls"], label_visibility="collapsed")

    if not uploaded:
        st.session_state.pop("_bulk_file_id", None)
        st.session_state.pop("_bulk_vresult", None)
        return

    # Excel-specific layout options
    is_excel = uploaded.name.lower().endswith((".xlsx", ".xls"))
    excel_header_row = 1
    excel_usecols    = ""
    excel_sheet      = 0
    if is_excel:
        st.caption("Excel options — specify where your data is:")
        sheet_names = get_excel_sheet_names(uploaded.getvalue())
        if sheet_names:
            excel_sheet = st.selectbox("Sheet", options=sheet_names, index=0)
        ex_c1, ex_c2 = st.columns(2)
        excel_header_row = ex_c1.number_input("Header row #", min_value=1, step=1, value=1,
                                               help="Row number (1-based) containing the column headers.")
        excel_usecols    = ex_c2.text_input("Column range (optional)", value="",
                                             placeholder="e.g. B:S",
                                             help="Leave blank to read all columns.")

    # Validate once per unique file + Excel options combination
    file_id = f"{uploaded.name}_{uploaded.size}_{excel_sheet}_{excel_header_row}_{excel_usecols}"
    if st.session_state.get("_bulk_file_id") != file_id:
        st.session_state["_bulk_file_id"] = file_id
        with st.spinner("Validating…"):
            vresult = validate_csv(uploaded.getvalue(), filename=uploaded.name,
                                   excel_header_row=int(excel_header_row),
                                   excel_usecols=excel_usecols,
                                   excel_sheet=excel_sheet)
        st.session_state["_bulk_vresult"] = vresult

    vresult = st.session_state.get("_bulk_vresult", {})

    if not vresult.get("success"):
        st.error("❌ Validation failed — no deals will be added. Fix the errors below and re-upload.")
        for err in vresult.get("errors", []):
            st.markdown(f"- {err}")
        return

    # File is valid — show preview and await confirmation
    will_add = len(vresult["to_insert"])
    skipped  = vresult["skipped_names"]
    st.success(f"✓ File is valid — **{will_add}** deal(s) ready to add to the database.")
    if skipped:
        st.warning(
            f"⚠ {len(skipped)} deal(s) will be skipped (names already exist): "
            + ", ".join(f"**{n}**" for n in skipped)
        )

    _, mid, _ = st.columns([1, 2, 1])
    if mid.button("Confirm — Add to Database", type="primary", width="stretch"):
        with st.spinner("Adding deals…"):
            ins = insert_validated_rows(vresult["to_insert"])
        st.session_state.pop("_bulk_file_id", None)
        st.session_state.pop("_bulk_vresult", None)
        if ins["success"]:
            st.rerun()
        else:
            st.error(f"Insert failed: {ins['error']}")


if "add_expander_key" not in st.session_state:
    st.session_state.add_expander_key = 0
with st.expander("(+) Add Deal", expanded=False, key=f"add_expander_{st.session_state.add_expander_key}"):
    st.markdown('<div class="exp-add"></div>', unsafe_allow_html=True)
    # Bulk Add button
    _, _, _btn = st.columns([2, 2, 1])
    if _btn.button("⊞ Bulk Add", width="stretch"):
        _bulk_add_dialog()
    st.markdown('<hr style="margin-top:-0.1rem; border:none; border-top:1px solid rgba(255,255,255,0.15);">', unsafe_allow_html=True)


    copy_options = [_BLANK] + [d["deal_name"] for d in deals]
    if st.session_state.get("add_copy_from") not in copy_options:
        st.session_state["add_copy_from"] = _BLANK
    copy_from = st.selectbox("Copy from existing deal", options=copy_options, key="add_copy_from")
    t = deals[[d["deal_name"] for d in deals].index(copy_from)] if copy_from != _BLANK else {}

    with st.form("add_deal_form"):
        new_deal_name = st.text_input("Deal Name", value=t.get("deal_name", ""), placeholder="ex: Peachtree Corners NPL")

        c1, c2 = st.columns(2)
        new_date_received = c1.date_input("Date Received", value=_to_date(t.get("date_received", "")), format="YYYY-MM-DD", min_value=datetime.date(2000, 1, 1))
        new_date_closed   = c2.text_input("Date Closed (YYYY-MM-DD)", value=t.get("date_closed", ""), placeholder="Leave blank if not closed")

        c1, c2, c3 = st.columns([2, 2, 1])
        new_city     = c1.text_input("City",      value=t.get("city",     ""))
        new_states   = c2.multiselect("State(s)/Region",
                                      STATES, default=[x for x in t.get("states", []) if x in STATES])
        new_zip_code = c3.text_input("Zip Code",  value=t.get("zip_code", ""))

        c1, c2, c3 = st.columns(3)
        new_tcm_originator    = c1.text_input("TCM Originator",    value=t.get("tcm_originator",    ""))
        new_broker            = c2.text_input("Broker",            value=t.get("broker",            ""))
        new_brokerage_company = c3.text_input("Brokerage Company", value=t.get("brokerage_company", ""))

        c1, c2 = st.columns(2)
        new_fund_investment_amount = c1.number_input("Fund Investment Amount ($)", min_value=0, step=10000, value=int(t["fund_investment_amount"]) if t.get("fund_investment_amount") else None)
        new_deal_size              = c2.number_input("Deal Size ($)",              min_value=0, step=10000, value=int(t["deal_size"])              if t.get("deal_size")              else None)

        c1, c2 = st.columns(2)
        new_deal_type    = c1.text_input("Deal Type",    value=t.get("deal_type",    ""), placeholder="e.g. Debt, Equity, NPL")
        new_deal_subtype = c2.text_input("Deal Subtype", value=t.get("deal_subtype", ""), placeholder="e.g. Co-GP, First Lien, Mezz")

        c1, c2 = st.columns([3, 1])
        new_asset_class = c1.text_input("Asset Class", value=t.get("asset_class", ""), placeholder="e.g. Retail, Multifamily, Industrial")
        new_development = c2.selectbox("Development",  DEVELOPMENTS, index=_selectbox_index(DEVELOPMENTS, t.get("development", "")))

        c1, c2 = st.columns(2)
        new_stage  = c1.selectbox("Stage",  STAGES,   index=_selectbox_index(STAGES,   t.get("stage",  "")))
        new_status = c2.selectbox("Status", STATUSES, index=_selectbox_index(STATUSES, t.get("status", "")))

        _, add_mid, _ = st.columns([1, 0.75, 1])
        add_submitted = add_mid.form_submit_button("Add  +", type="primary", width="stretch")

    if add_submitted:
        existing_names = {d["deal_name"].strip().lower() for d in all_deals}
        if not new_deal_name.strip():
            st.error("Deal Name cannot be empty.")
        elif new_deal_name.strip().lower() in existing_names:
            st.error(f"A deal named '{new_deal_name.strip()}' already exists. Use a unique name.")
        else:
            added = add_deal(
                deal_name              = new_deal_name.strip(),
                date_received          = new_date_received.isoformat(),
                date_closed            = new_date_closed.strip(),
                city                   = new_city,
                states                 = new_states,
                zip_code               = new_zip_code,
                tcm_originator         = new_tcm_originator,
                broker                 = new_broker,
                brokerage_company      = new_brokerage_company,
                fund_investment_amount = int(new_fund_investment_amount) if new_fund_investment_amount is not None else 0,
                deal_size              = int(new_deal_size)              if new_deal_size              is not None else 0,
                deal_type              = new_deal_type,
                deal_subtype           = new_deal_subtype,
                asset_class            = new_asset_class,
                development            = new_development,
                stage                  = new_stage,
                status                 = new_status,
            )
            if added:
                st.session_state.add_expander_key += 1
                st.success(f"'{new_deal_name.strip()}' added. ↺ Refresh to see it in the table.")
            else:
                st.error("Failed to add deal.")

# --- Delete Form ➖---
@st.dialog("Bulk Delete — Select Range")
def _bulk_delete_range_dialog():
    st.write("Enter the **#** range of deals to delete. All deals whose # falls within this range will be removed.")
    col1, col2 = st.columns(2)
    min_id = col1.number_input("Min #", min_value=1, step=1, value=1)
    max_id = col2.number_input("Max #", min_value=1, step=1, value=1)

    if min_id > max_id:
        st.warning("Min # must be ≤ Max #.")
        return

    preview = get_all_deals({"id": {"$gte": int(min_id), "$lte": int(max_id)}})
    if preview:
        st.info(f"**{len(preview)}** deal(s) in range #{int(min_id)} – #{int(max_id)}:")
        for d in preview:
            st.caption(f"#{d['id']} — {d['deal_name']}")
    else:
        st.info(f"No deals found in range #{int(min_id)} – #{int(max_id)}.")

    _, mid, _ = st.columns([1, 2, 1])
    if mid.button("Confirm Range", type="primary", width="stretch", disabled=not preview):
        st.session_state["_bulk_del_range"] = {
            "min_id": int(min_id),
            "max_id": int(max_id),
            "names":  [d["deal_name"] for d in preview],
            "count":  len(preview),
        }
        st.rerun()


@st.dialog("Confirm Bulk Delete")
def _bulk_delete_confirm_dialog():
    r = st.session_state["_bulk_del_range"]
    st.warning(
        f"Are you sure you want to permanently delete **{r['count']}** deal(s) "
        f"(# {r['min_id']} – # {r['max_id']})? This cannot be undone."
    )
    for name in r["names"]:
        st.caption(f"• {name}")
    st.write("")
    yes_col, no_col = st.columns(2)
    if yes_col.button("Yes, delete all", type="primary", width="stretch"):
        deleted = delete_deals_by_range(r["min_id"], r["max_id"])
        st.session_state.pop("_bulk_del_range", None)
        st.session_state.delete_expander_key = st.session_state.get("delete_expander_key", 0) + 1
        st.rerun()
    if no_col.button("No, cancel", width="stretch"):
        st.session_state.pop("_bulk_del_range", None)
        st.rerun()


if "delete_expander_key" not in st.session_state:
    st.session_state.delete_expander_key = 0
with st.expander("(–) Delete Deal", expanded=False, key=f"delete_expander_{st.session_state.delete_expander_key}"):
    st.markdown('<div class="exp-delete"></div>', unsafe_allow_html=True)
    _, _, _btn = st.columns([2, 2, 1])
    if _btn.button("⊟ Bulk Delete", width="stretch"):
        _bulk_delete_range_dialog()
    st.markdown('<hr style="margin-top:0.3rem; margin-bottom:0.4rem; border:none; border-top:1px solid rgba(255,255,255,0.15);">', unsafe_allow_html=True)
    if not deals:
        st.warning("No deals match the current filters." if filters else "No deals available to delete.")
    else:
        del_lookup = {d["deal_name"]: d for d in deals}
        del_options = list(del_lookup.keys())
        if st.session_state.get("delete_selected_deal") not in del_options:
            st.session_state["delete_selected_deal"] = del_options[0]
        delete_selected = st.selectbox("Select Deal", options=del_options, key="delete_selected_deal")
        st.write("")
        _, del_mid, _ = st.columns([1, 0.75, 1])
        if del_mid.button("🗑 Delete Deal", type="primary", width="stretch"):
            st.session_state["pending_delete_id"]   = del_lookup[delete_selected]["id"]
            st.session_state["pending_delete_name"] = delete_selected

@st.dialog("Confirm Delete")
def _confirm_delete_dialog():
    name = st.session_state.get("pending_delete_name", "this deal")
    st.warning(f"Are you sure you want to permanently delete **'{name}'**? This cannot be undone.")
    yes_col, no_col = st.columns(2)
    if yes_col.button("Yes, delete that shit", type="primary", width="stretch"):
        deleted = delete_deal(st.session_state["pending_delete_id"])
        st.session_state.pop("pending_delete_id",   None)
        st.session_state.pop("pending_delete_name", None)
        if deleted:
            st.session_state["selected_deal"] = None
            st.session_state.delete_expander_key += 1
            st.rerun()
        else:
            st.error("Delete failed.")
    if no_col.button("No, keep that shit", width="stretch"):
        st.session_state.pop("pending_delete_id",   None)
        st.session_state.pop("pending_delete_name", None)
        st.rerun()

if st.session_state.get("pending_delete_id"):
    _confirm_delete_dialog()

if st.session_state.get("_bulk_del_range"):
    _bulk_delete_confirm_dialog()
