from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from database import get_db
import json

router = APIRouter(prefix="/objectives", tags=["objectives"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def objectives_list(request: Request):
    db = get_db()
    try:
        chapters = db.execute("SELECT id, title FROM chapters ORDER BY \"order\"").fetchall()
        objectives = db.execute("""
            SELECT lo.*, c.title as chapter_title
            FROM learning_objectives lo
            JOIN chapters c ON lo.chapter_id = c.id
            ORDER BY c."order", lo.id
        """).fetchall()
    finally:
        db.close()
    return templates.TemplateResponse("objectives/list.html", {
        "request": request,
        "chapters": chapters,
        "objectives": objectives,
    })


@router.get("/api", response_class=JSONResponse)
async def objectives_data():
    db = get_db()
    try:
        rows = db.execute("""
            SELECT lo.*, c.title as chapter_title
            FROM learning_objectives lo
            JOIN chapters c ON lo.chapter_id = c.id
            ORDER BY c."order", lo.id
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()
