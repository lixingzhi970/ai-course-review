from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from database import get_db
import json
import random

router = APIRouter(prefix="/review", tags=["review"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def review_home(request: Request):
    db = get_db()
    try:
        chapters = db.execute("SELECT id, title FROM chapters ORDER BY \"order\"").fetchall()
        # Stats
        total_practice = db.execute("SELECT COUNT(*) as c FROM study_records").fetchone()["c"]
        wrong_count = db.execute("SELECT COUNT(DISTINCT question_id) as c FROM study_records WHERE is_correct = 0").fetchone()["c"]
        weak_chapters = db.execute("""
            SELECT c.title, COUNT(sr.id) as wrong_count
            FROM study_records sr
            JOIN questions q ON sr.question_id = q.id
            JOIN chapters c ON q.chapter_id = c.id
            WHERE sr.is_correct = 0
            GROUP BY c.id ORDER BY wrong_count DESC LIMIT 3
        """).fetchall()
    finally:
        db.close()
    return templates.TemplateResponse("review/home.html", {
        "request": request,
        "chapters": chapters,
        "total_practice": total_practice,
        "wrong_count": wrong_count,
        "weak_chapters": weak_chapters,
    })


@router.get("/summary", response_class=HTMLResponse)
async def chapter_summaries(request: Request, chapter_id: int = 0):
    db = get_db()
    try:
        chapters = db.execute("SELECT id, title FROM chapters ORDER BY \"order\"").fetchall()
        selected = None
        concepts = []
        objectives = []
        if chapter_id > 0:
            selected = db.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
            concepts = db.execute(
                "SELECT * FROM concepts WHERE chapter_id = ? ORDER BY is_key DESC, difficulty",
                (chapter_id,)
            ).fetchall()
            objectives = db.execute(
                "SELECT * FROM learning_objectives WHERE chapter_id = ?", (chapter_id,)
            ).fetchall()
    finally:
        db.close()
    return templates.TemplateResponse("review/summary.html", {
        "request": request,
        "chapters": chapters,
        "selected": selected,
        "concepts": concepts,
        "objectives": objectives,
        "chapter_id": chapter_id,
    })


@router.get("/cards", response_class=HTMLResponse)
async def concept_cards(request: Request, chapter_id: int = 0):
    db = get_db()
    try:
        chapters = db.execute("SELECT id, title FROM chapters ORDER BY \"order\"").fetchall()
        query = "SELECT c.*, ch.title as chapter_title FROM concepts c JOIN chapters ch ON c.chapter_id = ch.id"
        params = []
        if chapter_id > 0:
            query += " WHERE c.chapter_id = ?"
            params.append(chapter_id)
        query += " ORDER BY c.is_key DESC, RANDOM()"
        concepts = db.execute(query, params).fetchall()
    finally:
        db.close()
    return templates.TemplateResponse("review/cards.html", {
        "request": request,
        "chapters": chapters,
        "concepts": concepts,
        "chapter_id": chapter_id,
    })


@router.get("/wrong", response_class=HTMLResponse)
async def wrong_questions(request: Request):
    db = get_db()
    try:
        wrong = db.execute("""
            SELECT q.*, c.title as chapter_title,
                   (SELECT COUNT(*) FROM study_records sr2 WHERE sr2.question_id = q.id AND sr2.is_correct = 0) as wrong_times,
                   (SELECT MAX(sr.timestamp) FROM study_records sr WHERE sr.question_id = q.id AND sr.is_correct = 0) as last_wrong
            FROM questions q
            LEFT JOIN chapters c ON q.chapter_id = c.id
            WHERE q.id IN (SELECT DISTINCT question_id FROM study_records WHERE is_correct = 0)
            ORDER BY last_wrong DESC
        """).fetchall()
        # Recommendations based on weak areas
        weak_chapters = db.execute("""
            SELECT c.id, c.title, COUNT(sr.id) as wc
            FROM study_records sr
            JOIN questions q ON sr.question_id = q.id
            JOIN chapters c ON q.chapter_id = c.id
            WHERE sr.is_correct = 0
            GROUP BY c.id ORDER BY wc DESC LIMIT 3
        """).fetchall()
        recommendations = []
        for wc in weak_chapters:
            rec_qs = db.execute("""
                SELECT * FROM questions WHERE chapter_id = ? ORDER BY RANDOM() LIMIT 3
            """, (wc["id"],)).fetchall()
            recommendations.append({"chapter": wc, "questions": rec_qs})
    finally:
        db.close()

    wrong_with_options = []
    for w in wrong:
        wd = dict(w)
        wd["options"] = json.loads(w["options"]) if w["options"] else []
        wrong_with_options.append(wd)

    return templates.TemplateResponse("review/wrong.html", {
        "request": request,
        "wrong_questions": wrong_with_options,
        "recommendations": recommendations,
    })
