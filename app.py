"""Streamlit frontend. Talks to the FastAPI backend (main.py) over HTTP."""
import base64
import hmac
import os
import uuid

import requests
import streamlit as st
import streamlit.components.v1 as components

import doc_utils as D
import prompts as P
import theme

# ---------------------------------------------------------------------------
# Static credentials (fixed in code so nobody else can use the app)
# ---------------------------------------------------------------------------
USERNAME = "Niki"
PASSWORD = "Niki@1830"

DEFAULT_COLLEGE = "Kongu Engineering College"


def _backend_url():
    try:
        url = st.secrets.get("BACKEND_URL")
    except Exception:
        url = None
    return (url or os.environ.get("BACKEND_URL") or "http://localhost:8000").rstrip("/")


BACKEND = _backend_url()

MAX_FOLLOWUP_LEVELS = 3   # follow-up questions go at most 3 levels deep

st.set_page_config(page_title=P.APP_TITLE, layout="wide", initial_sidebar_state="expanded")
theme.apply_theme()


def top_bar(show_nav):
    """Logo + app title on the left, page links on the right (like the portfolio nav)."""
    if not show_nav:                      # login page: brand centred
        st.markdown(theme.logo_html(P.APP_TITLE, center=True), unsafe_allow_html=True)
        st.markdown("<div class='navline'></div>", unsafe_allow_html=True)
        return None
    left, right = st.columns([1.5, 1])
    with left:
        st.markdown(theme.logo_html(P.APP_TITLE), unsafe_allow_html=True)
    page = None
    if show_nav:
        with right:
            page = st.radio("Page", ["Chat", "Poster maker"], horizontal=True,
                            label_visibility="collapsed", key="page")
    st.markdown("<div class='navline'></div>", unsafe_allow_html=True)
    return page


def call_api(method, path, **kw):
    """Call the FastAPI backend with the pasted Groq key; raise RuntimeError(detail) on errors."""
    headers = {"X-Groq-Key": st.session_state.get("groq_key", "")}
    try:
        r = requests.request(method, BACKEND + path, headers=headers, timeout=180, **kw)
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Cannot reach the backend at {BACKEND}. Is `uvicorn main:api` running?")
    except requests.exceptions.Timeout:
        raise RuntimeError("The backend took too long to respond. Try again.")
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise RuntimeError(str(detail))
    return r.json()


def _same(a, b):
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


# ================================================================== login
def login_page():
    theme.center_layout()
    top_bar(False)
    theme.hero(center=True)
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        with st.form("login"):
            st.markdown("<div class='sec'>Sign in</div>", unsafe_allow_html=True)
            st.caption("Enter your credentials to continue.")
            u = st.text_input("User name")
            p = st.text_input("Password", type="password")
            ok = st.form_submit_button("Login", use_container_width=True)
        if ok:
            user_ok = _same(u.strip().lower(), USERNAME.lower())
            pass_ok = _same(p, PASSWORD)
            if user_ok and pass_ok:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Invalid user name or password.")


def key_box():
    """Groq key is pasted here at run time - never stored in code or on disk."""
    st.markdown("<div class='sec'>Groq API key</div>", unsafe_allow_html=True)
    key = st.text_input("Paste your Groq API key", type="password",
                        value=st.session_state.get("groq_key", ""),
                        placeholder="gsk_...", help="Kept only in this browser session.")
    st.session_state.groq_key = key.strip()
    if not st.session_state.groq_key:
        st.warning("Paste your key to start chatting.")
    st.caption(f"Backend: {BACKEND}")
    return bool(st.session_state.groq_key)


# ============================================================ page 1: chat
def chat_page(has_key):
    ss = st.session_state
    ss.setdefault("messages", [])
    ss.setdefault("loaded", [])
    ss.setdefault("pending", None)
    ss.setdefault("pending_depth", 0)

    with st.sidebar:
        st.markdown("<div class='sec'>Documents</div>", unsafe_allow_html=True)
        files = st.file_uploader("PDF, Word, Excel, PowerPoint, text, CSV or image (OCR)",
                                 accept_multiple_files=True,
                                 type=["pdf", "docx", "xlsx", "xls", "pptx", "txt", "csv", "md",
                                       "json", "png", "jpg", "jpeg", "tif", "bmp", "webp"])
        if files and st.button("Extract and load", use_container_width=True):
            with st.spinner("Extracting content (OCR runs on scanned pages)..."):
                try:
                    res = call_api("POST", "/extract", data={"session_id": ss.sid},
                                   files=[("files", (f.name, f.getvalue())) for f in files])
                    ss.loaded = res["loaded"]
                    for w in res["warnings"]:
                        st.warning(w)
                    if ss.loaded:
                        st.success(f"Loaded {len(ss.loaded)} file(s).")
                except RuntimeError as e:
                    st.error(str(e))
        if ss.loaded:
            st.caption("Loaded: " + ", ".join(ss.loaded))
            if st.button("Clear documents", use_container_width=True):
                try:
                    call_api("DELETE", f"/session/{ss.sid}")
                except RuntimeError:
                    pass
                ss.loaded = []
                st.rerun()
        st.info("Creator mode: ask me to *make a poster / image / PPT / PDF / Word / Excel / text file "
                "on a topic*. Posters and images use the header set on the Poster maker page.")
        if st.button("New chat", use_container_width=True):
            ss.messages = []
            st.rerun()

    if not ss.messages:
        theme.hero()
    st.markdown("<div class='sec'>Chat</div>", unsafe_allow_html=True)
    st.markdown("#### Ask the Food Technologist or create something")
    if not has_key:
        st.info("Paste your Groq API key in the left sidebar (under Groq API key) to start.")

    for i, m in enumerate(ss.messages):
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m.get("style"):
                st.caption(f"Reply style: {m['style']}")
            for k, f in enumerate(m.get("files") or []):
                raw = base64.b64decode(f["b64"])
                if f["ext"] == "png":
                    st.image(raw)
                st.download_button(f"Download {f['ext'].upper()}", raw,
                                   file_name=f"niki_food_tech.{f['ext']}", mime=f["mime"],
                                   key=f"dl{i}_{k}")
    last = ss.messages[-1] if ss.messages else None
    if last and last.get("followups") and last.get("depth", 0) < MAX_FOLLOWUP_LEVELS:
        level = last.get("depth", 0) + 1
        st.caption(f"Suggested follow-up questions (level {level} of {MAX_FOLLOWUP_LEVELS})")
        for j, q in enumerate(last["followups"]):
            if st.button(q, key=f"fu{len(ss.messages)}_{j}"):
                ss.pending = q
                ss.pending_depth = level
                st.rerun()
    elif last and last.get("depth", 0) >= MAX_FOLLOWUP_LEVELS:
        st.caption("Follow-up limit reached. Ask a new question to start again.")

    typed = st.chat_input("Ask a question, or say: make a poster on probiotic yogurt",
                          disabled=not has_key)
    if ss.pending:
        query, depth = ss.pending, ss.pending_depth
    else:
        query, depth = typed, 0           # a typed question starts a fresh follow-up chain
    ss.pending, ss.pending_depth = None, 0
    if not query:
        return

    history = [{"role": m["role"], "content": m["content"]} for m in ss.messages]
    last_style = next((m.get("style") for m in reversed(ss.messages) if m["role"] == "assistant"), None)
    ss.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    with st.chat_message("assistant"):
        with st.spinner("Thinking like a food technologist..."):
            try:
                res = call_api("POST", "/chat", json={"session_id": ss.sid, "query": query,
                                                      "history": history,
                                                      "headers": ss.get("hdr_fields", []),
                                                      "last_style": last_style,
                                                      "depth": depth})
                msg = {"role": "assistant", "content": res["answer"], "followups": res["followups"],
                       "files": res.get("files", []), "style": res.get("style"), "depth": depth}
            except RuntimeError as e:
                msg = {"role": "assistant", "content": f"Sorry Niki, {e}", "depth": MAX_FOLLOWUP_LEVELS}
        ss.messages.append(msg)
    st.rerun()


# ========================================================== page 2: poster
def poster_page(has_key):
    ss = st.session_state
    ss.setdefault("hdr_fields", [])
    ss.setdefault("college_confirm", None)

    st.markdown("<div class='sec'>Poster maker</div>", unsafe_allow_html=True)
    st.markdown("#### Design a poster from a title")
    left, right = st.columns([1, 1.3])

    with left:
        st.markdown("**1. Header content**")
        kind = st.selectbox("Header option", ["College name", "Project title", "Assignment"])
        size = st.selectbox("Font size", ["h1", "h2"], key="hsize")
        value = None

        if kind == "College name":
            st.write(f"Do you want to use **{DEFAULT_COLLEGE}**?")
            c1, c2 = st.columns(2)
            if c1.button("Yes, use it"):
                ss.college_confirm = "yes"
            if c2.button("No, I'll type it"):
                ss.college_confirm = "no"
            if ss.college_confirm == "yes":
                value = DEFAULT_COLLEGE
            elif ss.college_confirm == "no":
                value = st.text_input("College name") or None
        elif kind == "Project title":
            value = st.text_input("Project title") or None
        else:
            t1 = st.text_input("Assignment title")
            extra = [st.text_input(f"Title {n} (optional)") for n in (2, 3, 4)]
            parts = [t for t in [t1] + extra if t.strip()]
            value = " - ".join(parts) if parts else None
            if value:
                st.caption("Header preview: " + value)

        if st.button("Add to header", disabled=not value):
            ss.hdr_fields.append({"value": value, "size": size})
            st.rerun()

        with st.expander("Add another custom header field"):
            cv = st.text_input("Custom text", key="cust")
            cs = st.selectbox("Font size ", ["h1", "h2"], key="csize")
            if st.button("Add custom field") and cv.strip():
                ss.hdr_fields.append({"value": cv.strip(), "size": cs})
                st.rerun()

        if ss.hdr_fields:
            st.markdown("**Current header**")
            for i, h in enumerate(ss.hdr_fields):
                a, b = st.columns([6, 1])
                a.write(f"`{h['size']}` {h['value']}")
                if b.button("Remove", key=f"rm{i}"):
                    ss.hdr_fields.pop(i)
                    st.rerun()

        st.markdown("**2. Poster title**")
        title = st.text_input("Poster title (food technology topic)")
        go = st.button("Generate poster", type="primary",
                       disabled=not (title.strip() and has_key))

    with right:
        if go:
            with st.spinner("Designing poster..."):
                try:
                    res = call_api("POST", "/poster", json={"title": title.strip()})
                    ss.poster = {"title": title.strip(), "content": res["content"]}
                except RuntimeError as e:
                    st.warning(str(e))
        if ss.get("poster"):
            pt, pc = ss.poster["title"], ss.poster["content"]
            hdrs = ss.hdr_fields or [{"value": P.APP_TITLE, "size": "h2"}]
            html = D.poster_html(hdrs, pt, pc)
            components.html("<style>body{margin:0;background:#060a14}</style>" + html,
                            height=900, scrolling=True)
            c1, c2, c3 = st.columns(3)
            c1.download_button("Download PNG", D.poster_png(hdrs, pt, pc),
                               "poster.png", "image/png")
            c2.download_button("Download PDF", D.poster_pdf(hdrs, pt, pc),
                               "poster.pdf", "application/pdf")
            c3.download_button("Download HTML", html, "poster.html", "text/html")


# ==================================================================== main
def main():
    if not st.session_state.get("auth"):
        login_page()
        return
    st.session_state.setdefault("sid", uuid.uuid4().hex)
    page = top_bar(True)
    with st.sidebar:
        has_key = key_box()
        st.divider()
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
        st.divider()
    (chat_page if page == "Chat" else poster_page)(has_key)


main()
