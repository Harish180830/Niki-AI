"""Document extraction (with OCR), TF-IDF retrieval (RAG) and file export."""
import io
import re


# =============================================================== extraction
def _ocr_image(img):
    try:
        import pytesseract
        return pytesseract.image_to_string(img)
    except Exception:
        return ""


def _pdf_text(data):
    text_pages = []
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        text_pages = [(p.extract_text() or "") for p in reader.pages]
    except Exception:
        pass
    # OCR fallback for scanned pages
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        doc = fitz.open(stream=data, filetype="pdf")
        for i, page in enumerate(doc):
            if i >= len(text_pages):
                text_pages.append("")
            if len(text_pages[i].strip()) < 25:
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                text_pages[i] = _ocr_image(img)
    except Exception:
        pass
    return "\n\n".join(f"[Page {i+1}]\n{t}" for i, t in enumerate(text_pages) if t.strip())


def extract_text(name, data):
    ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
    if ext == "pdf":
        return _pdf_text(data)
    if ext == "docx":
        import docx
        d = docx.Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs if p.text.strip()]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text.strip() for c in row.cells))
        return "\n".join(parts)
    if ext in ("xlsx", "xlsm", "xls"):
        import pandas as pd
        sheets = pd.read_excel(io.BytesIO(data), sheet_name=None)
        return "\n\n".join(f"[Sheet {n}]\n{df.to_csv(index=False)}" for n, df in sheets.items())
    if ext == "pptx":
        from pptx import Presentation
        prs = Presentation(io.BytesIO(data))
        out = []
        for i, s in enumerate(prs.slides, 1):
            texts = [sh.text_frame.text for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.strip()]
            out.append(f"[Slide {i}]\n" + "\n".join(texts))
        return "\n\n".join(out)
    if ext in ("png", "jpg", "jpeg", "bmp", "tif", "tiff", "webp"):
        from PIL import Image
        return _ocr_image(Image.open(io.BytesIO(data)))
    # txt, csv, md, json, anything else readable
    return data.decode("utf-8", errors="ignore")


# ================================================================ retrieval
class Retriever:
    """TF-IDF retriever - no embedding model download needed."""

    def __init__(self, docs, chunk_size=900, overlap=150):
        self.chunks = []  # (source, text)
        for name, text in docs.items():
            text = re.sub(r"[ \t]+", " ", text)
            i = 0
            while i < len(text):
                piece = text[i:i + chunk_size].strip()
                if piece:
                    self.chunks.append((name, piece))
                i += chunk_size - overlap
        self.vec = self.matrix = None
        if self.chunks:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
            self.matrix = self.vec.fit_transform([c[1] for c in self.chunks])

    def search(self, query, k=5):
        if not self.chunks:
            return []
        from sklearn.metrics.pairwise import linear_kernel
        scores = linear_kernel(self.vec.transform([query]), self.matrix).ravel()
        top = scores.argsort()[::-1][:k]
        return [self.chunks[i] for i in top if scores[i] > 0]

    def context(self, query, k=5):
        hits = self.search(query, k)
        if not hits and self.chunks:           # generic request ("summarise this") -> first chunks
            hits = self.chunks[:k]
        return "\n\n".join(f"[source: {s}]\n{t}" for s, t in hits)


# ================================================================== export
def _clean(s):
    return re.sub(r"[*_`#]", "", str(s))


def to_txt(d):
    lines = [d["title"], "=" * len(d["title"]), ""]
    for s in d["sections"]:
        lines.append(s["heading"])
        if s.get("paragraph"):
            lines.append(_clean(s["paragraph"]))
        lines += [f"  - {_clean(b)}" for b in s.get("bullets", [])]
        lines.append("")
    if d.get("table"):
        t = d["table"]
        lines.append(" | ".join(map(str, t["columns"])))
        lines += [" | ".join(map(str, r)) for r in t["rows"]]
    return "\n".join(lines).encode("utf-8")


def to_docx(d):
    import docx
    doc = docx.Document()
    doc.add_heading(d["title"], 0)
    for s in d["sections"]:
        doc.add_heading(s["heading"], 1)
        if s.get("paragraph"):
            doc.add_paragraph(_clean(s["paragraph"]))
        for b in s.get("bullets", []):
            doc.add_paragraph(_clean(b), style="List Bullet")
    t = d.get("table")
    if t and t.get("columns"):
        tbl = doc.add_table(rows=1, cols=len(t["columns"]))
        tbl.style = "Light Grid Accent 1"
        for i, c in enumerate(t["columns"]):
            tbl.rows[0].cells[i].text = str(c)
        for r in t["rows"]:
            cells = tbl.add_row().cells
            for i, v in enumerate(r[:len(cells)]):
                cells[i].text = str(v)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def to_pdf(d):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape
    ss = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=d["title"])
    story = [Paragraph(escape(d["title"]), ss["Title"]), Spacer(1, 12)]
    for s in d["sections"]:
        story.append(Paragraph(escape(s["heading"]), ss["Heading2"]))
        if s.get("paragraph"):
            story.append(Paragraph(escape(_clean(s["paragraph"])), ss["BodyText"]))
        for b in s.get("bullets", []):
            story.append(Paragraph("&bull; " + escape(_clean(b)), ss["BodyText"]))
        story.append(Spacer(1, 8))
    t = d.get("table")
    if t and t.get("columns"):
        data = [[Paragraph(escape(str(c)), ss["BodyText"]) for c in row]
                for row in [t["columns"]] + t["rows"]]
        tbl = Table(data, repeatRows=1)
        tbl.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                                 ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey)]))
        story.append(tbl)
    doc.build(story)
    return buf.getvalue()


def to_xlsx(d):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = "Content"
    ws.append([d["title"]])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([])
    ws.append(["Section", "Details"])
    for c in ws[3]:
        c.font = Font(bold=True)
    for s in d["sections"]:
        if s.get("paragraph"):
            ws.append([s["heading"], _clean(s["paragraph"])])
        for b in s.get("bullets", []):
            ws.append([s["heading"], _clean(b)])
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 100
    t = d.get("table")
    if t and t.get("columns"):
        w2 = wb.create_sheet("Table")
        w2.append([str(c) for c in t["columns"]])
        for c in w2[1]:
            c.font = Font(bold=True)
        for r in t["rows"]:
            w2.append([str(v) for v in r])
        for col in w2.columns:
            w2.column_dimensions[col[0].column_letter].width = 24
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def to_pptx(d):
    from pptx import Presentation
    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[0])
    s.shapes.title.text = d["title"]
    s.placeholders[1].text = "Niki AI Assistance for Food Technology"
    for sec in d["sections"]:
        sl = prs.slides.add_slide(prs.slide_layouts[1])
        sl.shapes.title.text = sec["heading"]
        tf = sl.placeholders[1].text_frame
        items = list(sec.get("bullets", []))
        if sec.get("paragraph"):
            items.insert(0, sec["paragraph"])
        tf.text = _clean(items[0]) if items else ""
        for it in items[1:7]:
            tf.add_paragraph().text = _clean(it)
        for p in tf.paragraphs:
            for r in p.runs:
                r.font.size = __import__("pptx.util", fromlist=["Pt"]).Pt(20)
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


EXPORTERS = {
    "txt": (to_txt, "text/plain", "txt"),
    "docx": (to_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
    "pdf": (to_pdf, "application/pdf", "pdf"),
    "xlsx": (to_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
    "pptx": (to_pptx, "application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx"),
}


def export(fmt, structure):
    fn, mime, ext = EXPORTERS[fmt]
    return fn(structure), mime, ext


# ================================================================== poster
def poster_html(headers, title, content):
    """headers: list of dict(value, size) where size in {'h1','h2'}."""
    from html import escape as e
    hdr = "".join(f"<{h['size']} class='hd'>{e(h['value'])}</{h['size']}>" for h in headers)
    secs = "".join(
        f"<div class='card'><h3>{e(s['heading'])}</h3><ul>"
        + "".join(f"<li>{e(p)}</li>" for p in s["points"]) + "</ul></div>"
        for s in content.get("sections", []))
    return f"""<div style="font-family:Segoe UI,Arial,sans-serif;max-width:760px;margin:auto;
background:linear-gradient(160deg,#060a14,#0b1226);border:6px solid #4d9aff;border-radius:14px;padding:28px;color:#e6edf7">
<style>.hd{{text-align:center;margin:4px 0;color:#7ab8ff}}h1.hd{{font-size:34px}}h2.hd{{font-size:24px}}
.card{{background:#0b1226;border:1px solid #1c2747;border-radius:10px;padding:10px 16px;margin:10px 0;box-shadow:0 1px 4px #0003}}
.card h3{{margin:4px 0;color:#4d9aff}}.card li{{margin:4px 0;font-size:15px}}</style>
{hdr}<hr style="border:1px solid #4d9aff">
<div style="text-align:center;font-size:30px;font-weight:700;margin:14px 0">{e(title)}</div>
<div style="text-align:center;font-style:italic;margin-bottom:12px">{e(content.get('tagline',''))}</div>
{secs}
<div style="text-align:center;margin-top:14px;font-weight:600">{e(content.get('footer',''))}</div></div>"""


def poster_pdf(headers, title, content):
    from reportlab.lib.pagesizes import A3
    from reportlab.lib.utils import simpleSplit
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    W, H = A3
    c = canvas.Canvas(buf, pagesize=A3)
    c.setFillColor(colors.HexColor("#060a14"))
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#4d9aff"))
    c.setLineWidth(10)
    c.rect(20, 20, W - 40, H - 40)
    y = H - 90
    c.setFillColor(colors.HexColor("#7ab8ff"))
    for h in headers:
        size = 40 if h["size"] == "h1" else 28
        c.setFont("Helvetica-Bold", size)
        for line in simpleSplit(h["value"], "Helvetica-Bold", size, W - 120):
            c.drawCentredString(W / 2, y, line)
            y -= size + 8
    y -= 20
    c.setFillColor(colors.HexColor("#e6edf7"))
    c.setFont("Helvetica-Bold", 34)
    for line in simpleSplit(title, "Helvetica-Bold", 34, W - 120):
        c.drawCentredString(W / 2, y, line)
        y -= 44
    c.setFont("Helvetica-Oblique", 18)
    c.drawCentredString(W / 2, y, content.get("tagline", "")[:90])
    y -= 50
    for s in content.get("sections", []):
        c.setFillColor(colors.HexColor("#4d9aff"))
        c.setFont("Helvetica-Bold", 24)
        c.drawString(70, y, s["heading"])
        y -= 32
        c.setFillColor(colors.HexColor("#e6edf7"))
        c.setFont("Helvetica", 16)
        for p in s["points"]:
            lines = simpleSplit("- " + p, "Helvetica", 16, W - 160)
            for ln in lines:
                c.drawString(85, y, ln)
                y -= 22
            y -= 4
        y -= 18
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(W / 2, 60, content.get("footer", ""))
    c.showPage()
    c.save()
    return buf.getvalue()


# ============================================================ image output
# Poster / infographic PNGs are drawn with Pillow (designed layouts, not AI photos).
_BOLD = ["arialbd.ttf", "C:/Windows/Fonts/arialbd.ttf", "DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/Library/Fonts/Arial Bold.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]
_REG = ["arial.ttf", "C:/Windows/Fonts/arial.ttf", "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf"]


def _font(size, bold=False):
    from PIL import ImageFont
    for p in (_BOLD if bold else _REG):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for w in str(text).split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _centered(draw, text, size, bold, fill, y, W, margin, gap=1.25):
    f = _font(size, bold)
    for line in _wrap(draw, text, f, W - 2 * margin):
        tw = draw.textlength(line, font=f)
        draw.text(((W - tw) / 2, y), line, font=f, fill=fill)
        y += int(size * gap)
    return y


def _card(draw, x, y, w, section, scale, paint=True, force_h=None):
    """White rounded card with heading + bullet points. Returns its natural height."""
    hs, ps = int(38 * scale), int(28 * scale)
    pad = int(24 * scale)
    hf, pf = _font(hs, True), _font(ps)
    indent = int(32 * scale)
    head = _wrap(draw, section["heading"], hf, w - 2 * pad)
    pts = [_wrap(draw, p, pf, w - 2 * pad - indent) for p in section["points"]]
    h = pad + len(head) * int(hs * 1.3) + int(10 * scale)
    h += sum(len(p) * int(ps * 1.35) + int(10 * scale) for p in pts) + pad
    if paint:
        draw.rounded_rectangle([x, y, x + w, y + (force_h or h)], radius=22, fill="#0b1226",
                               outline="#1c2747", width=3)
        cy = y + pad
        for line in head:
            draw.text((x + pad, cy), line, font=hf, fill="#4d9aff")
            cy += int(hs * 1.3)
        cy += int(10 * scale)
        for lines in pts:
            draw.text((x + pad, cy), "\u2022", font=pf, fill="#4d9aff")
            for line in lines:
                draw.text((x + pad + indent, cy), line, font=pf, fill="#e6edf7")
                cy += int(ps * 1.35)
            cy += int(10 * scale)
    return h


def _png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def poster_png(headers, title, content, W=1240):
    """Portrait poster (A4 ratio, grows taller if the content needs it). Returns PNG bytes."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, 6000), "#060a14")
    d = ImageDraw.Draw(img)
    m, y = 60, 90
    for h in headers:
        y = _centered(d, h["value"], 64 if h["size"] == "h1" else 44, True, "#7ab8ff", y, W, m + 20)
        y += 6
    y += 10
    d.line([(m + 20, y), (W - m - 20, y)], fill="#4d9aff", width=5)
    y += 35
    y = _centered(d, title, 76, True, "#e6edf7", y, W, m + 20, 1.3) + 10
    if content.get("tagline"):
        y = _centered(d, content["tagline"], 36, False, "#9fb0cc", y, W, m + 20, 1.35) + 10
    y += 20
    for s in content.get("sections", []):
        y += _card(d, m + 20, y, W - 2 * m - 40, s, 1.0) + 26
    if content.get("footer"):
        y = _centered(d, content["footer"], 34, True, "#7ab8ff", y + 10, W, m + 20)
    H = max(1754, y + m)
    img = img.crop((0, 0, W, H))
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, W - 21, H - 21], outline="#4d9aff", width=12)
    return _png_bytes(img)


def infographic_png(headers, title, content, W=1600):
    """Landscape infographic with a 2-column card grid. Returns PNG bytes."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, 5000), "#060a14")
    d = ImageDraw.Draw(img)
    m, y = 60, 60
    for h in headers:
        y = _centered(d, h["value"], 40 if h["size"] == "h1" else 30, True, "#7ab8ff", y, W, m)
    y += 8
    d.line([(m, y), (W - m, y)], fill="#4d9aff", width=4)
    y += 28
    y = _centered(d, title, 66, True, "#e6edf7", y, W, m, 1.25) + 4
    if content.get("tagline"):
        y = _centered(d, content["tagline"], 30, False, "#9fb0cc", y, W, m, 1.35)
    y += 30
    gap = 30
    cw = (W - 2 * m - gap) // 2
    secs = content.get("sections", [])
    for i in range(0, len(secs), 2):
        row = secs[i:i + 2]
        rh = max(_card(d, 0, 0, cw, s, 0.85, paint=False) for s in row)
        for j, s in enumerate(row):
            _card(d, m + j * (cw + gap), y, cw, s, 0.85, force_h=rh)
        y += rh + gap
    if content.get("footer"):
        y = _centered(d, content["footer"], 30, True, "#7ab8ff", y, W, m)
    H = max(900, y + m)
    img = img.crop((0, 0, W, H))
    d = ImageDraw.Draw(img)
    d.rectangle([15, 15, W - 16, H - 16], outline="#4d9aff", width=10)
    return _png_bytes(img)
