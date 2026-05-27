# TCM.io — Proto 1.0

Internal toolset for commercial real estate credit analysis. [Lucid Chart](https://lucid.app/lucidchart/0e46a7e9-b874-4db2-96b5-d908a50d287b/edit?viewport_loc=276%2C-2344%2C4452%2C3120%2C0_0&invitationId=inv_ac9e2f59-9171-4006-be51-f9661f9a38cd)


---

## Project Structure

```
ToccoaIO/
├── main/
│   ├── app.py              # Streamlit entry point — auth gate + navigation shell
│   ├── LLM_service.py      # AI pipeline logic (Gemini + Claude)
│   ├── db/
│   │   └── mongo.py        # MongoDB connection and CRUD layer
│   └── pages/
│       ├── home.py                     # Welcome screen
│       ├── 1_Business_Development.py   # Deal pipeline (MongoDB)
│       ├── 2_Asset_Management.py       # Stub
│       ├── 3_Reporting.py              # Stub
│       ├── 4_Research.py               # Property research UI
│       └── 5_Extra.py                  # Placeholder
├── keys/                   # API credentials (not in git)
│   ├── gemini_key.txt
│   ├── claude_key.txt
│   ├── mongo.txt           # line 3 = full MongoDB URI
│   └── password.txt        # app passkey (local dev only)
├── analysis/               # Generated reports (auto-created, not in git)
├── requirements.txt
├── install_requirements.bat
└── APItest.py              # API connectivity check
```

---

## Setup

**Install dependencies** — run before any Python scripts:
```bash
install_requirements.bat
```
Or manually:
```bash
pip install -r requirements.txt
```

**Add API keys** (one key per file, no trailing newline):
```
keys/gemini_key.txt    ← Google Gemini API key
keys/claude_key.txt    ← Anthropic Claude API key
keys/mongo.txt         ← line 1: username, line 2: password, line 3: full URI
keys/password.txt      ← app passkey (local dev)
```

> **Streamlit Cloud deployment (for Devs):** Add the following secrets in the app dashboard:
> ```toml
> GEMINI_API_KEY = "..."
> CLAUDE_API_KEY = "..."
> MONGO_URI      = "mongodb+srv://..."
> PASSKEY        = "..."
> ```

**Verify API connectivity:**
```bash
python APItest.py
```

**Run the app:**
```bash
streamlit run main/app.py
```

---

## Authentication

All pages are gated behind a passkey screen on first visit. The gate is implemented in `app.py` and cannot be bypassed by navigating directly to a page URL. Key details:

- Token = `SHA-256(passkey + server_nonce)`, written to the URL on successful entry
- Server nonce is regenerated on every `streamlit run` — old session URLs are automatically invalidated
- Token is re-stamped on every page navigation so it survives Streamlit's URL changes
- 2 failed attempts triggers a 5-second lockout with the form disabled
- `secrets.compare_digest` used for constant-time comparison

---

## App Structure

`app.py` uses `st.navigation()` for multi-page routing — calling it before the auth check suppresses Streamlit's sidebar auto-discovery and gives full control over what renders.

| Page | Status | Description |
|---|---|---|
| **Home** | Live | Welcome screen and module index |
| **Business Development** | Live | Deal pipeline backed by MongoDB |
| **Asset Management** | Coming soon | Portfolio monitoring |
| **Reporting** | Coming soon | Report generation and exports |
| **Research** | Live | AI-powered property and tenant research |
| **Extra** | Placeholder | Additional models and tools |

---

## Business Development — MongoDB Deal Pipeline

The **Business Development** page is backed by a MongoDB Atlas cluster (`toccoaIO_db` / `deal_pipeline` collection).

### Connection (`db/mongo.py`)

`get_mongo_client()` is decorated with `@st.cache_resource` so the connection is created once per server lifetime and reused across all reruns. Credential resolution:

1. `keys/mongo.txt` line 3 — local development
2. `st.secrets["MONGO_URI"]` — Streamlit Cloud deployment

### Deal Schema (18 fields)

| Field | Type | Notes |
|---|---|---|
| `id` | int | Auto-increment, read-only |
| `date_received` | string | YYYY-MM-DD |
| `deal_name` | string | |
| `city` | string | |
| `state` | string | 2-letter abbreviation |
| `zip_code` | string | |
| `tcm_originator` | string | |
| `broker` | string | |
| `brokerage_company` | string | |
| `fund_investment_amount` | float | Dollar amount |
| `deal_size` | float | Dollar amount |
| `deal_type` | string | Free text |
| `deal_subtype` | string | Free text |
| `asset_class` | string | Free text |
| `development` | string | Yes / No |
| `stage` | string | Dropdown — see `STAGES` in `mongo.py` |
| `status` | string | Active / Inactive |
| `date_closed` | string | YYYY-MM-DD, blank if not closed |

### UI Features

- Sortable, horizontally-scrollable dataframe of all deals
- Sidebar filters by Stage and Status
- Collapsible **Edit Deal** expander with a full form for all 18 fields
- Changes are written back to MongoDB via `update_deal()` using `$set`

---

## Future Updates / In Development

### Business Development — Deal Pipeline

| Feature | Status | Description |
|---|---|---|
| **Add Deal +** | Planned | A form for submitting new deals directly from the UI into the MongoDB collection, auto-incrementing the `id` field |
| **Delete Deal** | Planned | A module to permanently remove a deal from the collection — TBD whether implemented as a button within the Edit Deal expander or as a separate collapsible section |

---

## Research Pipeline

The **Research** tab runs a two-stage AI pipeline given a property address and optional tenant name.

### Stage 1 — Gemini Web Research (`research_property`)

Model: `gemini-2.5-flash` with **Google Search grounding** enabled.

Performs live web searches across four categories:

| Category | What It Looks For |
|---|---|
| **Building Permits & NOC** | Recent permit filings, notice of commencement, scope of work, permit status |
| **Tenant / Business News** | Closures, expansions, relocations, lease activity, financial stress signals |
| **Vacancy & Listing Status** | (if no tenant) Active listings, listing broker, vacancy duration, prior tenants |
| **Public Records** | Tax liens, zoning changes, recent sales, ownership transfers, code violations |

### Stage 2 — Claude Report Synthesis (`synthesize_report`)

Model: `claude-haiku-4-5-20251001`, max 1500 tokens.

Transforms raw Gemini research into a structured credit intelligence memo with five sections:

1. **Property Overview** — asset type, location context, use class
2. **Tenant Health** or **Vacancy & Marketability** — depends on whether a tenant was provided
3. **Red Flags** — concerns for a commercial lender
4. **Positive Signals** — factors supporting creditworthiness or stability
5. **Analyst Summary** — 2–3 sentence bottom-line risk read with due diligence recommendations

### Stage 3 — Output

Report is saved to `/analysis/` as a timestamped markdown file and displayed in the UI. A **Download Report** button is available at the top of the result for local export.

> **Note:** On Streamlit Cloud the filesystem is ephemeral — reports are not persisted across sessions. Download the report before closing.

---

## Pipeline Summary

```
User Input: Address + (optional) Tenant Name
        ↓
[Gemini] Live web search across 4 research categories
        ↓
[Claude] Synthesize into 5-section credit memo
        ↓
[Output] Markdown report displayed in UI + download button
```

---

## Example Inputs

- **Address:** `3065 Peachtree Industrial Blvd, Atlanta, GA`
- **Tenant:** `Walgreens` (leave blank for vacant property analysis)
