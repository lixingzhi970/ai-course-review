"""AI课程期末复习平台 — 人工智能通识基础（大模型篇）

A comprehensive review platform for the AI General Education course.
"""
import os
import json
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from database import init_db

app = FastAPI(title="AI课程复习平台")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates are loaded via Jinja2 in each module
from routes import chapters, questions, objectives, review, updates, import_data, generate

app.include_router(chapters.router)
app.include_router(questions.router)
app.include_router(objectives.router)
app.include_router(review.router)
app.include_router(updates.router)
app.include_router(import_data.router)
app.include_router(generate.router)


@app.on_event("startup")
async def startup():
    init_db()
    # Auto-seed on first run (e.g. Render's ephemeral filesystem)
    from database import get_db
    db = get_db()
    try:
        count = db.execute("SELECT COUNT(*) as c FROM chapters").fetchone()["c"]
        if count == 0:
            db.close()
            import seed_data
            seed_data.seed()
            try:
                import enrich_data
                enrich_data.generate_all_question_types()
                enrich_data.seed_knowledge_updates()
                enrich_data.import_all_pdfs()
            except Exception as e:
                print(f"Enrichment skipped (e.g. PDF dir not available): {e}")
        else:
            db.close()
    except Exception:
        try:
            db.close()
        except:
            pass


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    from fastapi.templating import Jinja2Templates
    from database import get_db
    templates = Jinja2Templates(directory="templates")
    db = get_db()
    try:
        chapters_count = db.execute("SELECT COUNT(*) as c FROM chapters").fetchone()["c"]
        questions_count = db.execute("SELECT COUNT(*) as c FROM questions").fetchone()["c"]
        concepts_count = db.execute("SELECT COUNT(*) as c FROM concepts").fetchone()["c"]
        updates_count = db.execute("SELECT COUNT(*) as c FROM knowledge_updates").fetchone()["c"]

        # Study stats
        total_attempts = db.execute("SELECT COUNT(*) as c FROM study_records").fetchone()["c"]
        correct_attempts = db.execute("SELECT COUNT(*) as c FROM study_records WHERE is_correct = 1").fetchone()["c"]
        accuracy = round(correct_attempts / total_attempts * 100, 1) if total_attempts > 0 else 0

        # Recent wrong questions
        wrong_questions = db.execute("""
            SELECT sr.id, q.stem, q.type, q.difficulty, c.title as chapter_title, sr.timestamp
            FROM study_records sr
            JOIN questions q ON sr.question_id = q.id
            LEFT JOIN chapters c ON q.chapter_id = c.id
            WHERE sr.is_correct = 0
            ORDER BY sr.timestamp DESC LIMIT 5
        """).fetchall()

        chapters_list = db.execute("SELECT * FROM chapters ORDER BY \"order\"").fetchall()
    finally:
        db.close()

    stats = {
        "chapters": chapters_count,
        "questions": questions_count,
        "concepts": concepts_count,
        "updates": updates_count,
        "total_attempts": total_attempts,
        "accuracy": accuracy,
    }

    return templates.TemplateResponse("index.html", {
        "request": request,
        "stats": stats,
        "chapters": chapters_list,
        "wrong_questions": wrong_questions,
    })


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
