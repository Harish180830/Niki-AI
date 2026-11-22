"""Theme matching harish180830.github.io: near-black navy, electric-blue accent,
Inter for text and JetBrains Mono for labels, bordered dark cards."""
import streamlit as st

BG = "#060a14"
CARD = "#0b1226"
LINE = "#1c2747"
BLUE = "#4d9aff"
TEXT = "#e6edf7"
MUTED = "#9fb0cc"

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
.stApp{background:radial-gradient(900px 480px at 88% 6%,rgba(40,100,200,.30),transparent 62%),radial-gradient(600px 400px at 5% 60%,rgba(40,100,200,.10),transparent 65%),#060a14;color:#e6edf7;font-family:'Inter',sans-serif}
html,body,[class*="st-"],button,input,textarea{font-family:'Inter',sans-serif}
header[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:1.2rem;padding-left:2rem;padding-right:2rem;max-width:1100px;margin-left:0;margin-right:auto}
h1,h2,h3,h4{color:#fff;letter-spacing:-0.01em}
section[data-testid="stSidebar"]{background:#080d1c;border-right:1px solid #1c2747}
section[data-testid="stSidebar"] *{color:#cfd9ee}
.topbar{display:flex;align-items:center;gap:12px;padding:6px 0}
.logo{font-family:'JetBrains Mono',monospace;font-weight:500;color:#4d9aff;border:1px dashed #4d9aff;border-radius:6px;padding:4px 8px;font-size:.95rem}
.brand{font-weight:600;color:#fff;font-size:1.05rem}
.navline{border-top:1px solid #1c2747;margin:4px 0 18px}
div[role="radiogroup"]{justify-content:flex-end;gap:6px}
div[role="radiogroup"] label{background:transparent;border:1px solid transparent;border-radius:8px;padding:4px 12px;font-family:'JetBrains Mono',monospace}
div[role="radiogroup"] label>div:first-child{display:none}
div[role="radiogroup"] label:hover{border-color:#1c2747}
div[role="radiogroup"] label:has(input:checked){border-color:#4d9aff;color:#4d9aff}
div[role="radiogroup"] label p{font-family:'JetBrains Mono',monospace;font-size:.88rem;color:inherit}
.hero h1{font-size:clamp(2rem,4.6vw,3.7rem);font-weight:800;line-height:1.08;margin:.2rem 0 .6rem;letter-spacing:-0.025em}
.hl{color:#4d9aff;text-shadow:0 0 28px rgba(77,154,255,.5)}
.sub{font-size:1.15rem;color:#b4c3df;margin-bottom:.6rem}
.tags{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
.tags span{font-family:'JetBrains Mono',monospace;font-size:.78rem;border:1px solid #1c2747;border-radius:999px;padding:3px 12px;color:#9fb0cc;background:rgba(11,18,38,.7)}
.stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"]>button{background:transparent;border:1px solid #1c2747;color:#e6edf7;border-radius:8px;font-family:'JetBrains Mono',monospace;font-size:.85rem}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:#4d9aff;color:#4d9aff;background:rgba(77,154,255,.06)}
.stButton>button[kind="primary"],[data-testid="stBaseButton-primary"],[data-testid="stFormSubmitButton"]>button{background:#4d9aff;border-color:#4d9aff;color:#06101f;font-weight:600}
.stButton>button[kind="primary"]:hover,[data-testid="stFormSubmitButton"]>button:hover{background:#6aaeff;color:#06101f}
input,textarea,[data-baseweb="select"]>div,[data-baseweb="input"]{background:#0b1226!important;border-color:#1c2747!important;color:#e6edf7!important;border-radius:8px!important}
[data-testid="stForm"]{background:rgba(11,18,38,.85);border:1px solid #1c2747;border-radius:12px;padding:1.2rem}
[data-testid="stFileUploaderDropzone"]{background:#0b1226;border:1px dashed #1c2747;border-radius:10px}
[data-testid="stChatMessage"]{background:rgba(11,18,38,.85);border:1px solid #1c2747;border-radius:12px}
[data-testid="stChatInput"]{background:#0b1226;border:1px solid #1c2747;border-radius:14px}
[data-testid="stBottom"]>div{background:transparent}
[data-testid="stAlert"]{background:rgba(77,154,255,.08);border:1px solid #1c2747;border-radius:10px}
[data-testid="stCaptionContainer"]{font-family:'JetBrains Mono',monospace;color:#9fb0cc}
hr{border-color:#1c2747}
.sec{font-family:'JetBrains Mono',monospace;color:#4d9aff;font-size:.8rem;letter-spacing:.08em;text-transform:uppercase;margin:6px 0 2px}
.stButton>button{text-align:left;justify-content:flex-start}
.topbar.center{justify-content:center}
.hero.center{text-align:center}
.hero.center .tags{justify-content:center}
</style>"""

CENTER_CSS = """<style>
.block-container{max-width:1000px;margin-left:auto;margin-right:auto;padding-top:3rem}
[data-testid="stForm"] .sec{text-align:center}
[data-testid="stForm"] [data-testid="stCaptionContainer"]{text-align:center;margin-bottom:.6rem}
</style>"""


def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)


def center_layout():
    """Login page only: centre the whole page content."""
    st.markdown(CENTER_CSS, unsafe_allow_html=True)


def logo_html(title, center=False):
    cls = "topbar center" if center else "topbar"
    return f"<div class='{cls}'><span class='logo'>NF</span><span class='brand'>{title}</span></div>"


def hero(center=False):
    tags = "".join(f"<span>{t}</span>" for t in ["PDF", "PPTX", "DOCX", "XLSX", "PNG", "OCR", "RAG"])
    cls = "hero center" if center else "hero"
    st.markdown(
        f"<div class='{cls}'><h1>Niki AI Assistance<br><span class='hl'>for Food Technology</span></h1>"
        "<div class='sub'>Food science · Processing · Quality · Safety, powered by Groq</div>"
        f"<div class='tags'>{tags}</div></div>",
        unsafe_allow_html=True)
