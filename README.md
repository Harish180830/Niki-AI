# Niki AI Assistance for Food Technology

Food-technology chatbot: **Streamlit** frontend + **FastAPI** backend + **LangChain ChatGroq**
(model `openai/gpt-oss-120b`). The Groq API key is pasted in the app sidebar while it runs -
it is never stored in code, files or GitHub.

```
Streamlit (app.py)  --HTTP + X-Groq-Key header-->  FastAPI (main.py)  -->  ChatGroq (core.py)
  login, chat, poster maker                          /extract /chat /poster /health
```

## What it does
- **Ask** food-technology questions; upload PDF / Word / Excel / PPT / text / images (OCR) and ask about them.
- **Create from chat** and download the result:

  | Say this | You get |
  |---|---|
  | `make a poster on probiotic yogurt` | poster as PNG + PDF (uses the header from the Poster Maker page) |
  | `generate an image / infographic of milk pasteurization` | infographic PNG |
  | `create a pptx about HACCP` | PowerPoint |
  | `make a pdf / word document / excel sheet / text file on shelf life of bread` | PDF / DOCX / XLSX / TXT |
  | `download this as pdf` | the previous answer exported as that format |

  Images are designed layouts drawn by the app (not AI-generated photos).
- **Poster Maker page**: header (college name / project title / assignment, h1 or h2) + PNG/PDF/HTML download.
- **Random reply styles**: every reply starts with a "Hey Niki..." greeting and switches randomly between
  styles chosen by the kind of message (greeting, question, document question, creation) - e.g. Patient mentor,
  Concise expert, Exam coach, Lab partner, Document analyst, Creative studio. It never repeats the same style twice in a row.
  Edit `STYLES` in `prompts.py` to add your own.
- **Follow-up questions**: after each answer, 3 suggested follow-ups appear. Clicking one gives a deeper answer with new follow-ups, up to 3 levels; typing a new question starts a fresh chain.
- **Guardrails**: keyword filter + safety check + food-technology scope check on every request.

## Run locally (Windows / Linux / Mac)
```bash
pip install -r requirements.txt
# optional OCR engine for scanned files: Tesseract (Windows: UB-Mannheim installer)

# terminal 1
python -m uvicorn main:api --port 8000
# terminal 2
python -m streamlit run app.py
```
Open http://localhost:8501, log in, paste your Groq key in the sidebar.
Login is fixed in `app.py` (`USERNAME`, `PASSWORD`) - change it.

## Put it on GitHub
```bash
git init && git add . && git commit -m "Niki AI Assistance for Food Technology"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```
GitHub stores the code (and runs the CI check in `.github/workflows`) but cannot run a Python server:

1. **Backend (FastAPI)** - Render: New > Blueprint (uses `render.yaml` + `Dockerfile`, which installs Tesseract).
   Check `<url>/health` returns `{"status":"ok"}`.
2. **Frontend (Streamlit)** - https://share.streamlit.io > New app > main file `app.py`.
   In Settings > Secrets add: `BACKEND_URL = "https://<your-render-url>"`.

## Files
`app.py` UI · `theme.py` look and feel (dark navy + blue, matches harish180830.github.io; also `.streamlit/config.toml`) · `main.py` API routes · `core.py` ChatGroq pipeline, creation mode, style switching ·
`prompts.py` guardrail, persona, styles, task prompts · `doc_utils.py` extraction, retrieval, exports, poster/image rendering ·
`Dockerfile`, `render.yaml`, `.github/workflows/ci.yml`

## Notes
- Model name is in `MODELS` in `core.py`; check https://console.groq.com/docs/models if it is ever retired.
- Uploaded-document text is kept in backend memory per session (lost on restart).
