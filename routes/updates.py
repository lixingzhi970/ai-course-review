from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database import get_db

router = APIRouter(prefix="/updates", tags=["updates"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def updates_list(request: Request):
    db = get_db()
    try:
        updates = db.execute("""
            SELECT ku.*, c.title as chapter_title
            FROM knowledge_updates ku
            LEFT JOIN chapters c ON ku.related_chapter_id = c.id
            ORDER BY ku.created_at DESC
        """).fetchall()
        chapters = db.execute("SELECT id, title FROM chapters ORDER BY \"order\"").fetchall()
    finally:
        db.close()
    return templates.TemplateResponse("updates/list.html", {
        "request": request,
        "updates": updates,
        "chapters": chapters,
    })


@router.post("/add")
async def add_update(
    request: Request,
    title: str = Form(...),
    summary: str = Form(...),
    source: str = Form(""),
    source_date: str = Form(""),
    related_chapter_id: int = Form(0),
    related_concept: str = Form(""),
    relevance_note: str = Form(""),
):
    db = get_db()
    try:
        db.execute(
            """INSERT INTO knowledge_updates (title, summary, source, source_date, related_chapter_id, related_concept, relevance_note)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title, summary, source, source_date,
             related_chapter_id if related_chapter_id > 0 else None,
             related_concept, relevance_note),
        )
        db.commit()
    finally:
        db.close()
    return RedirectResponse(url="/updates", status_code=303)


@router.get("/api", response_class=JSONResponse)
async def updates_api():
    db = get_db()
    try:
        updates = db.execute("""
            SELECT ku.*, c.title as chapter_title
            FROM knowledge_updates ku
            LEFT JOIN chapters c ON ku.related_chapter_id = c.id
            ORDER BY ku.created_at DESC
        """).fetchall()
        return [dict(u) for u in updates]
    finally:
        db.close()
