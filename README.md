# TCM.io — Proto 1.0

AI-powered internal toolset for commercial real estate credit analysis.

---

## Project Structure

```
ToccoaIO/
├── main/
│   ├── app.py              # Streamlit entry point — navigation shell
│   ├── backend.py          # AI pipeline logic (Gemini + Claude)
│   └── pages/
│       ├── home.py                     # Welcome screen
│       ├── 1_Business_Development.py   # Stub
│       ├── 2_Asset_Management.py       # Stub
│       ├── 3_Reporting.py              # Stub
│       ├── 4_Research.py               # Property research UI
│       └── 5_Extra.py                  # Placeholder
├── keys/                   # API credentials (not in git)
│   ├── gemini_key.txt
│   └── claude_key.txt
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
keys/gemini_key.txt   ← Google Gemini API key
keys/claude_key.txt   ← Anthropic Claude API key
```

> **Streamlit Cloud deployment (for Devs):** Add keys as secrets in the app dashboard:
> ```toml
> GEMINI_API_KEY = "..."
> CLAUDE_API_KEY = "..."
> ```

**Verify connectivity:**
```bash
python APItest.py
```

**Run the app:**
```bash
streamlit run main/main.py
```

---

## App Structure

The app uses Streamlit's `st.navigation()` for multi-page routing. `app.py` is the shell — it sets page config and registers all pages. Navigation is persistent across all pages via the left sidebar.

| Page | Status | Description |
|---|---|---|
| **Home** | Live | Welcome screen and module index |
| **Business Development** | Coming soon | Pipeline and deal tracking |
| **Asset Management** | Coming soon | Portfolio monitoring |
| **Reporting** | Coming soon | Report generation and exports |
| **Research** | Live | AI-powered property and tenant research |
| **Extra** | Placeholder | Additional models and tools |

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

The prompt adapts based on whether a tenant name was provided.

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
