from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from templates_helper import render
from database import get_db
import json
import time

router = APIRouter(prefix="/practice", tags=["practice"])


@router.get("/", response_class=HTMLResponse)
async def practice_home(request: Request):
    db = get_db()
    try:
        chapters = db.execute("SELECT id, title FROM chapters ORDER BY \"order\"").fetchall()

        counts = {
            "single": db.execute("SELECT COUNT(*) as c FROM questions WHERE type='single'").fetchone()["c"],
            "multiple": db.execute("SELECT COUNT(*) as c FROM questions WHERE type='multiple'").fetchone()["c"],
            "judge": db.execute("SELECT COUNT(*) as c FROM questions WHERE type='judge'").fetchone()["c"],
            "short": db.execute("SELECT COUNT(*) as c FROM questions WHERE type='short'").fetchone()["c"],
            "case": db.execute("SELECT COUNT(*) as c FROM questions WHERE type='case'").fetchone()["c"],
        }
    finally:
        db.close()
    return render("practice/home.html", {
        "request": request,
        "active_page": "('practice', 'practice')",
        "chapters": chapters,
        "counts": counts,
    })


@router.get("/quiz", response_class=HTMLResponse)
async def quiz_page(request: Request, chapter: int = 0, type: str = "", difficulty: str = "", count: int = 10):
    db = get_db()
    try:
        query = "SELECT * FROM questions WHERE 1=1"
        params = []
        if chapter > 0:
            query += " AND chapter_id = ?"
            params.append(chapter)
        if type:
            query += " AND type = ?"
            params.append(type)
        if difficulty:
            query += " AND difficulty = ?"
            params.append(difficulty)

        query += " ORDER BY RANDOM() LIMIT ?"
        params.append(count)
        questions = db.execute(query, params).fetchall()
        chapter_map = {
            r["id"]: r["title"]
            for r in db.execute("SELECT id, title FROM chapters").fetchall()
        }
    finally:
        db.close()

    questions_json = []
    for q in questions:
        qd = dict(q)
        qd["options"] = json.loads(q["options"]) if q["options"] else []
        qd["chapter_title"] = chapter_map.get(q["chapter_id"], "")
        questions_json.append(qd)

    return render("practice/quiz.html", {
        "request": request,
        "active_page": "('practice', 'practice')",
        "questions": questions_json,
        "total": len(questions_json),
    })


@router.post("/submit", response_class=JSONResponse)
async def submit_answer(request: Request):
    data = await request.json()
    question_id = data.get("question_id")
    user_answer = data.get("answer")

    db = get_db()
    try:
        question = db.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        if not question:
            return {"error": "题目不存在"}

        correct = question["answer"].strip()
        user = user_answer.strip()

        is_correct = 1 if user == correct else 0

        db.execute(
            "INSERT INTO study_records (question_id, user_answer, is_correct) VALUES (?, ?, ?)",
            (question_id, user_answer, is_correct),
        )
        db.commit()

        return {
            "correct": is_correct == 1,
            "correct_answer": correct,
            "explanation": question["explanation"],
            "user_answer": user_answer,
        }
    finally:
        db.close()


@router.get("/result", response_class=HTMLResponse)
async def quiz_result(request: Request):
    db = get_db()
    try:
        records = db.execute("""
            SELECT sr.*, q.stem, q.answer, q.explanation, q.type, q.difficulty,
                   c.title as chapter_title
            FROM study_records sr
            JOIN questions q ON sr.question_id = q.id
            LEFT JOIN chapters c ON q.chapter_id = c.id
            ORDER BY sr.timestamp DESC LIMIT 50
        """).fetchall()
    finally:
        db.close()

    total = len(records)
    correct = sum(1 for r in records if r["is_correct"])
    wrong = total - correct
    accuracy = round(correct / total * 100, 1) if total > 0 else 0

    return render("practice/result.html", {
        "request": request,
        "active_page": "('practice', 'practice')",
        "records": records,
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "accuracy": accuracy,
    })


@router.get("/api/questions", response_class=JSONResponse)
async def get_questions(chapter_id: int = 0, type: str = "", difficulty: str = ""):
    db = get_db()
    try:
        query = "SELECT * FROM questions WHERE 1=1"
        params = []
        if chapter_id > 0:
            query += " AND chapter_id = ?"
            params.append(chapter_id)
        if type:
            query += " AND type = ?"
            params.append(type)
        if difficulty:
            query += " AND difficulty = ?"
            params.append(difficulty)

        questions = db.execute(query + " ORDER BY id", params).fetchall()
        result = []
        for q in questions:
            qd = dict(q)
            qd["options"] = json.loads(q["options"]) if q["options"] else []
            result.append(qd)
        return result
    finally:
        db.close()
