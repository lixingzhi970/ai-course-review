"""AI课程期末复习平台 — 人工智能通识基础（大模型篇）

A comprehensive review platform for the AI General Education course.
"""
import os
import json
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from database import init_db

import traceback as _tb
from fastapi.responses import PlainTextResponse

app = FastAPI(title="AI课程复习平台")


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    return PlainTextResponse(
        f"500 Internal Server Error\n\n{type(exc).__name__}: {exc}\n\n{_tb.format_exc()}",
        status_code=500,
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    return PlainTextResponse(
        f"500 Internal Server Error\n\n{type(exc).__name__}: {exc}\n\n{_tb.format_exc()}",
        status_code=500,
    )

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
    # Auto-seed on first run
    from database import get_db
    db = None
    try:
        db = get_db()
        count = db.execute("SELECT COUNT(*) as c FROM chapters").fetchone()["c"]
        if count == 0:
            db.close()
            db = None
            import seed_data
            seed_data.seed()
            import enrich_data
            try:
                enrich_data.generate_all_question_types()
                enrich_data.seed_knowledge_updates()
            except Exception:
                pass
    except Exception:
        pass
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


@app.get("/debug")
async def debug():
    """Diagnostic endpoint to check system health."""
    import traceback, os
    result = {
        "cwd": os.getcwd(),
        "files": os.listdir(".")[:20],
        "template_dir_exists": os.path.exists("templates"),
    }
    try:
        from templates_helper import render, BASE_DIR
        result["template_base_dir"] = BASE_DIR
        result["template_files"] = os.listdir(os.path.join(BASE_DIR, "templates"))[:20]
        result["templates_ok"] = True
    except Exception as e:
        result["templates_error"] = str(e)
        result["traceback"] = traceback.format_exc()

    # Try rendering a page and capture the error
    try:
        from database import get_db
        db = get_db()
        chapters = db.execute("SELECT * FROM chapters ORDER BY \"order\"").fetchall()
        db.close()
        render("index.html", {
            "request": {"url": type('obj', (object,), {"path": "/"})()},
            "active_page": "home",
            "stats": {"chapters": 9, "questions": 26, "concepts": 26, "updates": 8, "total_attempts": 0, "accuracy": 0},
            "chapters": chapters,
            "wrong_questions": [],
        })
        result["render_test"] = "OK"
    except Exception as e:
        result["render_error"] = str(e)
        result["render_traceback"] = traceback.format_exc()

    return result


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    from templates_helper import render
    from database import get_db
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

    return render("index.html", {
        "request": request,
        "active_page": "home",
        "stats": stats,
        "chapters": chapters_list,
        "wrong_questions": wrong_questions,
    })


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
