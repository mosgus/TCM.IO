# Toccoa.io — Proto 1.0

AI-powered commercial property and tenant research for credit analysts.

Given a property address and optional tenant name, the app uses a two-stage AI pipeline to produce a structured analyst report suitable for commercial lending decisions.

---

## Project Structure

```
ToccoaIO/
├── real_estate_intel/
│   ├── app.py          # Streamlit web UI
│   └── backend.py      # Core pipeline logic
├── analysis/           # Generated reports (auto-created)
├── keys/               # API credentials (not in git)
│   ├── gemini_key.txt
│   └── claude_key.txt
└── APItest.py             # API connectivity check
```

---

## Setup

**Install dependencies:**

Run `install_requirements.bat` (double-click or from terminal) before running any Python scripts:
```bash
install_requirements.bat
```
Or manually:
```bash
pip install -r requirements.txt
```

**Add API keys** (one key per file, no trailing newline required):
```
keys/gemini_key.txt   ← Google Gemini API key
keys/claude_key.txt   ← Anthropic Claude API key
```

**Verify connectivity:**
```bash
python APItest.py
```

**Run the app:**
```bash
streamlit run real_estate_intel/app.py
```

---

## How It Works

### Stage 1 — Gemini Web Research (`research_property`)

Model: `gemini-2.5-flash` with **Google Search grounding** enabled.

Gemini performs live web searches to gather current intelligence across four categories:

| Category | What It Looks For |
|---|---|
| **Building Permits & NOC** | Recent permit filings, notice of commencement, scope of work, permit status |
| **Tenant / Business News** | Closures, expansions, relocations, lease activity, financial stress signals |
| **Vacancy & Listing Status** | (if no tenant) Active for-sale/for-lease listings, listing broker, vacancy duration, prior tenants |
| **Public Records** | Tax liens, zoning changes, recent sales, ownership transfers, code violations |

The prompt adapts based on whether a tenant name was provided. Output is raw research text with citations where available.

---

### Stage 2 — Claude Report Synthesis (`synthesize_report`)

Model: `claude-haiku-4-5-20251001`, max 1500 tokens.

Claude acts as a **senior commercial real estate lending analyst** and transforms the raw Gemini research into a structured credit intelligence memo with five sections:

1. **Property Overview** — asset type, location context, use class
2. **Tenant Health** or **Vacancy & Marketability** — operational and financial signals, or vacancy/listing assessment
3. **Red Flags** — specific concerns for a commercial lender (liens, permit risk, vacancy duration, zoning)
4. **Positive Signals** — factors supporting creditworthiness or stability
5. **Analyst Summary** — 2–3 sentence bottom-line risk read with recommended due diligence items

The Claude prompt explicitly instructs a direct, analytical tone that acknowledges gaps in research rather than speculating.

---

### Stage 3 — Report Persistence (`save_analyst_report_md`)

Reports are saved to `/analysis/` as markdown files named:
```
YYYYMMDD_property-address-slug.md
```

The Streamlit UI also displays the raw Gemini research in a collapsible section as an audit trail.

---

## Pipeline Summary

```
User Input: Address + (optional) Tenant Name
        ↓
[Gemini] Live web search across 4 research categories
        ↓
[Claude] Synthesize into 5-section credit memo
        ↓
[Output] Markdown report saved to /analysis/ + displayed in UI
```

---

## Example Inputs

- **Address:** `3065 Peachtree Industrial Blvd, Atlanta, GA`
- **Tenant:** `Walgreens` (leave blank for vacant property analysis)
