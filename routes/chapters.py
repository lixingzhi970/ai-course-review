from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from templates_helper import render
from database import get_db
import json

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/", response_class=HTMLResponse)
async def knowledge_list(request: Request):
    db = get_db()
    try:
        chapters = db.execute("""
            SELECT c.*,
                   (SELECT COUNT(*) FROM concepts WHERE chapter_id = c.id) as concept_count,
                   (SELECT COUNT(*) FROM questions WHERE chapter_id = c.id) as question_count,
                   (SELECT COUNT(*) FROM learning_objectives WHERE chapter_id = c.id) as objective_count
            FROM chapters c ORDER BY c."order"
        """).fetchall()
    finally:
        db.close()
    return render("knowledge/list.html", {
        "request": request,
        "active_page": "('knowledge', 'knowledge')",
        "chapters": chapters,
    })


@router.get("/{chapter_id}", response_class=HTMLResponse)
async def chapter_detail(request: Request, chapter_id: int):
    db = get_db()
    try:
        chapter = db.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")
        concepts = db.execute(
            "SELECT * FROM concepts WHERE chapter_id = ? ORDER BY difficulty, is_key DESC",
            (chapter_id,)
        ).fetchall()
        objectives = db.execute(
            "SELECT * FROM learning_objectives WHERE chapter_id = ?",
            (chapter_id,)
        ).fetchall()
        questions = db.execute(
            "SELECT * FROM questions WHERE chapter_id = ? ORDER BY difficulty, type",
            (chapter_id,)
        ).fetchall()
        all_concepts = db.execute("SELECT id, name FROM concepts").fetchall()
    finally:
        db.close()

    # Parse related concept IDs
    concept_list = []
    for c in concepts:
        c_dict = dict(c)
        c_dict["related_ids"] = json.loads(c["related_concept_ids"]) if c["related_concept_ids"] else []
        concept_list.append(c_dict)

    # Build mindmap data for the chapter
    mindmap = {
        "nodes": [{"id": c["id"], "name": c["name"], "difficulty": c["difficulty"], "isKey": c["is_key"]}
                  for c in concept_list],
        "edges": []
    }
    for c in concept_list:
        for rid in c["related_ids"]:
            mindmap["edges"].append({"from": c["id"], "to": rid})

    return render("knowledge/detail.html", {
        "request": request,
        "active_page": "('knowledge', 'knowledge')",
        "chapter": chapter,
        "concepts": concept_list,
        "objectives": objectives,
        "questions": questions,
        "mindmap": mindmap,
    })
