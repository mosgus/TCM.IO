from pathlib import Path
import hashlib
import secrets
import time
import streamlit as st

APP_ICON      = Path(__file__).resolve().parent.parent / "app_assets" / "logo.PNG"
TCM_LOGO_TEXT = Path(__file__).resolve().parent.parent / "app_assets" / "logowText.PNG"

st.set_page_config(
    page_title="TCM.io",
    page_icon=str(APP_ICON),
    layout="centered"
)

# Define navigation first — suppresses auto-discovery, pg.run() only called after auth
pg = st.navigation([
    st.Page("pages/home.py",                   title="Home ⌂"),
    st.Page("pages/1_Business_Development.py", title="Business Development"),
    st.Page("pages/2_Asset_Management.py",     title="Asset Management"),
    st.Page("pages/3_Reporting.py",            title="Reporting"),
    st.Page("pages/4_Research.py",             title="Research"),
    st.Page("pages/5_Extra.py",                title="⋯"),
])


# --- Passkey auth ---

def _load_passkey() -> str:
    """Load passkey from keys/password.txt (local) or st.secrets (Streamlit Cloud)."""
    try:
        with open("keys/password.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return st.secrets["PASSKEY"]


@st.cache_resource
def _server_nonce() -> str:
    """Random value generated once per server start. Invalidates tokens from previous runs."""
    return secrets.token_hex(16)


def _make_token(passkey: str) -> str:
    """Return a hash of passkey + server nonce. Changes on every server restart."""
    return hashlib.sha256(f"{passkey}{_server_nonce()}".encode()).hexdigest()[:16]

# Render the passkey form as the full page — no dialog, no close button.
def _show_passkey_gate():

    st.markdown(
        """
        <style>
        html, body, [data-testid="stAppViewContainer"] {
            background: #0e1117 !important;
            color: #fafafa !important;
        }
        [data-testid="stAppViewContainer"] {
            background-image: radial-gradient(circle at top, rgba(79, 140, 255, 0.18), transparent 42%);
        }
        [data-testid="stAppViewBlockContainer"] {
            padding-top: 4rem;
        }
        [data-testid="stSidebar"]            { display: none !important; }
        [data-testid="collapsedControl"]     { display: none !important; }
        div[data-testid="InputInstructions"] { display: none !important; }
        input[type="password"]::-ms-reveal,
        input[type="password"]::-ms-clear,
        input[type="password"]::-webkit-credentials-auto-fill-button { display: none !important; }
        div[data-baseweb="input"] > div {
            background: #1a1f2b !important;
            border-color: rgba(255, 255, 255, 0.12) !important;
        }
        div[data-baseweb="input"] input {
            color: #fafafa !important;
        }
        button[kind="primary"] {
            background: #4f8cff !important;
            border-color: #4f8cff !important;
        }
        </style>
        """, # button
        unsafe_allow_html=True,
    )

    # Initialise lockout state
    if "failed_attempts" not in st.session_state:
        st.session_state.failed_attempts = 0
    if "locked_until" not in st.session_state:
        st.session_state.locked_until = 0.0

    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        st.image(str(TCM_LOGO_TEXT), width="stretch")
        st.write("")

        locked = time.time() < st.session_state.locked_until

        if locked:
            st.error("Too many failed attempts. Please wait.")

        st.write("Enter passkey to continue.")
        code = st.text_input("Passkey", type="password", label_visibility="collapsed", disabled=locked)
        if st.button("Enter", type="primary", width="stretch", disabled=locked):
            if secrets.compare_digest(code, _load_passkey()):
                st.session_state.authenticated  = True
                st.session_state.failed_attempts = 0
                st.query_params["t"] = _make_token(code)
                st.rerun()
            else:
                st.session_state.failed_attempts += 1
                if st.session_state.failed_attempts >= 2:
                    st.session_state.locked_until    = time.time() + 5
                    st.session_state.failed_attempts = 0
                    st.rerun()
                else:
                    st.error("Incorrect passkey.")

        if locked:
            time.sleep(max(0.0, st.session_state.locked_until - time.time()))
            st.rerun()


# Check URL token first — survives page refresh
if "authenticated" not in st.session_state:
    expected = _make_token(_load_passkey())
    st.session_state.authenticated = secrets.compare_digest(
        st.query_params.get("t", ""), expected
    )

if not st.session_state.authenticated:
    _show_passkey_gate()
    st.stop()

# Re-stamp token on every authenticated render so it survives page navigation
_expected = _make_token(_load_passkey())
if st.query_params.get("t") != _expected:
    st.query_params["t"] = _expected


# --- Run page (only reached after successful auth) ---

st.title("TCM.io")
pg.run()
