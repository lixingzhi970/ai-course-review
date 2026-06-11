from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse
from templates_helper import render
from database import get_db
import json, random

router = APIRouter(prefix="/exam", tags=["exam"])


@router.get("/", response_class=HTMLResponse)
async def exam_config(request: Request):
    """Exam paper configuration page."""
    db = get_db()
    try:
        chapters = db.execute("SELECT id, title FROM chapters ORDER BY \"order\"").fetchall()
        stats = {}
        for t in ["single", "multiple", "judge", "short", "case"]:
            for d in ["基础", "中等", "挑战"]:
                count = db.execute(
                    "SELECT COUNT(*) as c FROM questions WHERE type = ? AND difficulty = ?",
                    (t, d),
                ).fetchone()["c"]
                stats[f"{t}_{d}"] = count
    finally:
        db.close()

    return render("exam/config.html", {
        "request": request,
        "active_page": "exam",
        "chapters": chapters,
        "stats": stats,
    })


@router.get("/paper", response_class=HTMLResponse)
async def exam_paper(
    request: Request,
    single: int = Query(5, ge=0, le=30),
    multiple: int = Query(3, ge=0, le=20),
    judge: int = Query(5, ge=0, le=30),
    short: int = Query(2, ge=0, le=10),
    case: int = Query(1, ge=0, le=5),
    chapter_id: int = Query(0),
    difficulty: str = Query(""),
):
    """Generate and display the exam paper."""
    config = [
        ("single", single, "单选题"),
        ("multiple", multiple, "多选题"),
        ("judge", judge, "判断题"),
        ("short", short, "简答题"),
        ("case", case, "案例分析题"),
    ]

    db = get_db()
    try:
        selected = []
        for qtype, count, label in config:
            if count <= 0:
                continue
            query = "SELECT * FROM questions WHERE type = ?"
            params = [qtype]
            if chapter_id > 0:
                query += " AND chapter_id = ?"
                params.append(chapter_id)
            if difficulty:
                query += " AND difficulty = ?"
                params.append(difficulty)
            query += " ORDER BY RANDOM() LIMIT ?"
            params.append(count)

            questions = db.execute(query, params).fetchall()
            for i, q in enumerate(questions):
                qd = dict(q)
                qd["options"] = json.loads(q["options"]) if q["options"] else []
                qd["_index"] = len(selected) + 1
                selected.append(qd)
    finally:
        db.close()

    total_score = len([q for q in selected if q["type"] in ("single", "judge")]) * 2 + \
                  len([q for q in selected if q["type"] == "multiple"]) * 3 + \
                  len([q for q in selected if q["type"] == "short"]) * 8 + \
                  len([q for q in selected if q["type"] == "case"]) * 15

    type_labels = {"single": "单选题", "multiple": "多选题", "judge": "判断题", "short": "简答题", "case": "案例分析题"}

    return render("exam/paper.html", {
        "request": request,
        "active_page": "exam",
        "questions": selected,
        "total_score": total_score,
        "total_count": len(selected),
        "single": single, "multiple": multiple, "judge": judge, "short": short, "case": case,
        "chapter_id": chapter_id,
        "difficulty": difficulty,
        "type_labels": type_labels,
    })


@router.get("/answer", response_class=HTMLResponse)
async def exam_answer(
    request: Request,
    single: int = Query(5), multiple: int = Query(3),
    judge: int = Query(5), short: int = Query(2), case: int = Query(1),
    chapter_id: int = Query(0), difficulty: str = Query(""),
):
    """Answer key for the exam paper."""
    config = [
        ("single", single), ("multiple", multiple), ("judge", judge),
        ("short", short), ("case", case),
    ]

    db = get_db()
    try:
        selected = []
        for qtype, count in config:
            if count <= 0:
                continue
            query = "SELECT * FROM questions WHERE type = ?"
            params = [qtype]
            if chapter_id > 0:
                query += " AND chapter_id = ?"
                params.append(chapter_id)
            if difficulty:
                query += " AND difficulty = ?"
                params.append(difficulty)
            query += " ORDER BY RANDOM() LIMIT ?"
            params.append(count)
            questions = db.execute(query, params).fetchall()
            for i, q in enumerate(questions):
                qd = dict(q)
                qd["options"] = json.loads(q["options"]) if q["options"] else []
                qd["_index"] = len(selected) + 1
                selected.append(qd)
    finally:
        db.close()

    type_labels = {"single": "单选题", "multiple": "多选题", "judge": "判断题", "short": "简答题", "case": "案例分析题"}

    return render("exam/answer.html", {
        "request": request,
        "active_page": "exam",
        "questions": selected,
        "type_labels": type_labels,
    })
