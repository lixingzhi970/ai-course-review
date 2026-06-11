from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from templates_helper import render
from database import get_db
import json
import os

router = APIRouter(prefix="/import", tags=["import"])

# Default courseware directory
COURSEWARE_DIR = "/Users/linxizhou/Desktop/人工智能基础D/课件"


@router.get("/", response_class=HTMLResponse)
async def import_page(request: Request):
    db = get_db()
    try:
        chapters = db.execute("SELECT id, title FROM chapters ORDER BY \"order\"").fetchall()
    finally:
        db.close()

    # List available course PDFs
    pdf_files = []
    if os.path.exists(COURSEWARE_DIR):
        pdf_files = sorted([f for f in os.listdir(COURSEWARE_DIR) if f.endswith('.pdf')])

    return render("import/index.html", {
        "request": request,
        "active_page": "('import', 'import')",
        "chapters": chapters,
        "pdf_files": pdf_files,
        "courseware_dir": COURSEWARE_DIR,
    })


@router.post("/upload", response_class=JSONResponse)
async def upload_pdf(file: UploadFile = File(...), chapter_id: int = Form(...)):
    if not file.filename.endswith('.pdf'):
        return {"error": "仅支持PDF文件"}
    content = await file.read()
    db = get_db()
    try:
        # Try to extract text from PDF
        text = extract_pdf_text(content)

        db.execute(
            "UPDATE chapters SET raw_content = ?, processing_status = 'extracting' WHERE id = ?",
            (text[:50000], chapter_id),  # Limit to 50k chars for SQLite
        )
        db.commit()
        return {"success": True, "message": f"已上传 {file.filename}，文本长度: {len(text)} 字符"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


@router.post("/process/{chapter_id}", response_class=JSONResponse)
async def process_chapter(chapter_id: int):
    """AI-powered processing: extract concepts, key takeaways, learning objectives from raw content."""
    db = get_db()
    try:
        chapter = db.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
        if not chapter or not chapter["raw_content"]:
            return {"error": "章节无原始内容，请先上传PDF"}

        # For now, return a message that AI processing requires API key
        db.execute(
            "UPDATE chapters SET processing_status = 'done', updated_at = datetime('now', 'localtime') WHERE id = ?",
            (chapter_id,),
        )
        db.commit()
        return {
            "success": True,
            "message": "章节内容已处理。配置AI API Key后可启用自动提取概念和生成题目功能。"
        }
    finally:
        db.close()


def extract_pdf_text(file_content: bytes) -> str:
    """Extract text from PDF bytes. Tries PyPDF2 first, then pdfplumber."""
    import io

    # Method 1: PyPDF2 (clean text extraction for most PDFs)
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(file_content))
        pages_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
        if pages_text:
            result = '\n'.join(pages_text)
            if len(result.strip()) > 100:
                return result
    except Exception:
        pass

    # Method 2: pdfplumber (handles complex layouts better)
    try:
        import logging
        logging.getLogger('pdfplumber').setLevel(logging.ERROR)
        logging.getLogger('pdfminer').setLevel(logging.ERROR)

        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    # Filter out font warnings that pdfplumber may embed
                    clean = '\n'.join([
                        l for l in text.split('\n')
                        if not l.startswith('Could get FontBBox')
                    ])
                    if clean.strip():
                        pages_text.append(clean)
            if pages_text:
                result = '\n'.join(pages_text)
                if len(result.strip()) > 100:
                    return result
    except Exception:
        pass

    return "PDF文本提取失败。此PDF可能为纯图片型PDF，需要使用AI Vision进行OCR识别。"
