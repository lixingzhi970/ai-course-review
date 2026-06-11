"""AI-powered question generation module.

Uses OpenAI/Claude API to generate exam questions from course content.
Configure the API key via environment variable: AI_API_KEY
Configure the API base URL via: AI_API_BASE (defaults to https://api.anthropic.com)
Configure the model via: AI_MODEL (defaults to claude-sonnet-4-6)
"""
import os
import json
import httpx
from fastapi import APIRouter, Request, Form
from fastapi.responses import JSONResponse
from database import get_db

router = APIRouter(prefix="/api/generate", tags=["generate"])

AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_API_BASE = os.environ.get("AI_API_BASE", "https://api.anthropic.com")
AI_MODEL = os.environ.get("AI_MODEL", "claude-sonnet-4-6")


def build_question_prompt(chapter_content: str, objectives: list, question_type: str, difficulty: str, count: int = 3) -> str:
    """Build a prompt for generating exam questions."""
    type_desc = {
        "single": "单选题（4个选项，只有1个正确答案）",
        "multiple": "多选题（4个选项，至少有2个正确答案）",
        "judge": "判断题（判断陈述的正误）",
        "short": "简答题（需要3-5句话回答的概念性问题）",
        "case": "案例分析题（给出一个实际场景，要求运用课程知识进行分析）",
    }

    objectives_text = "\n".join([f"- {o['content_description']}: {o['objective']}" for o in objectives])

    prompt = f"""你是一位大学课程《人工智能通识基础（大模型篇）》的出题老师。请根据以下课程内容生成{count}道{type_desc.get(question_type, question_type)}。

## 课程内容
{chapter_content[:3000]}

## 学习目标
{objectives_text}

## 出题要求
1. 题目必须紧扣课程内容和学习目标
2. 难度等级：{difficulty}
3. 每道题必须包含：题干、正确答案、详细解析、对应的学习目标
4. 题目应该考察理解而非死记硬背
5. 选项要有干扰性但不能故意误导

请以JSON格式返回，格式如下：
```json
[
  {{
    "type": "{question_type}",
    "stem": "题干内容",
    "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
    "answer": "A",
    "explanation": "详细解析，说明为什么选这个答案，为什么不选其他选项",
    "difficulty": "{difficulty}",
    "source": "出自课程第X章XXX部分"
  }}
]
```"""
    return prompt


@router.post("/questions", response_class=JSONResponse)
async def generate_questions(
    chapter_id: int = Form(...),
    question_type: str = Form("single"),
    difficulty: str = Form("基础"),
    count: int = Form(3),
):
    """Generate questions using AI API."""
    if not AI_API_KEY:
        # Generate template questions without AI as fallback
        return generate_template_questions(chapter_id, question_type, difficulty, count)

    db = get_db()
    try:
        chapter = db.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
        if not chapter:
            return {"error": "章节不存在"}

        objectives = db.execute(
            "SELECT * FROM learning_objectives WHERE chapter_id = ?",
            (chapter_id,)
        ).fetchall()
        objectives_list = [dict(o) for o in objectives]
    finally:
        db.close()

    content = chapter["raw_content"] if chapter["raw_content"] else chapter["description"]
    prompt = build_question_prompt(content, objectives_list, question_type, difficulty, count)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{AI_API_BASE}/v1/messages",
                headers={
                    "x-api-key": AI_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": AI_MODEL,
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                text = data["content"][0]["text"]
                # Extract JSON from response
                json_match = text
                if "```json" in text:
                    json_match = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    json_match = text.split("```")[1].split("```")[0]

                questions = json.loads(json_match.strip())

                # Save generated questions to DB
                db2 = get_db()
                try:
                    for q in questions:
                        db2.execute(
                            """INSERT INTO questions (type, stem, options, answer, explanation, chapter_id, difficulty, source)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                q.get("type", question_type),
                                q["stem"],
                                json.dumps(q.get("options", []), ensure_ascii=False),
                                q["answer"],
                                q.get("explanation", ""),
                                chapter_id,
                                q.get("difficulty", difficulty),
                                q.get("source", ""),
                            ),
                        )
                    db2.commit()
                finally:
                    db2.close()

                return {"success": True, "questions": questions, "count": len(questions)}
            else:
                return {"error": f"API请求失败: {resp.status_code}", "detail": resp.text[:500]}
    except Exception as e:
        return {"error": f"AI调用出错: {str(e)}"}


def generate_template_questions(chapter_id: int, question_type: str, difficulty: str, count: int):
    """Generate template-based questions as fallback when no AI API key is configured."""
    db = get_db()
    try:
        chapter = db.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
        concepts = db.execute("SELECT * FROM concepts WHERE chapter_id = ?", (chapter_id,)).fetchall()
        objectives = db.execute("SELECT * FROM learning_objectives WHERE chapter_id = ?", (chapter_id,)).fetchall()
    finally:
        db.close()

    if not chapter:
        return {"error": "章节不存在"}

    questions = []
    concepts_list = [dict(c) for c in concepts]

    for i, concept in enumerate(concepts_list[:count]):
        q = generate_one_template_question(concept, question_type, difficulty, chapter["title"])
        if q:
            questions.append(q)

    # Save to DB
    db2 = get_db()
    try:
        for q in questions:
            db2.execute(
                """INSERT INTO questions (type, stem, options, answer, explanation, chapter_id, difficulty, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    q["type"], q["stem"], json.dumps(q.get("options", []), ensure_ascii=False),
                    q["answer"], q.get("explanation", ""), chapter_id,
                    q.get("difficulty", difficulty), q.get("source", ""),
                ),
            )
        db2.commit()
    finally:
        db2.close()

    return {"success": True, "questions": questions, "count": len(questions),
            "note": "题目为模板生成，建议配置AI_API_KEY环境变量以启用AI智能出题功能"}


def generate_one_template_question(concept: dict, qtype: str, difficulty: str, chapter_title: str) -> dict:
    """Generate a single template question from a concept."""
    name = concept["name"]
    explanation = concept["explanation"]

    if qtype == "single":
        # Create a multiple choice question by modifying the explanation
        correct = name
        distractors = [
            f"{name}仅适用于小规模模型",
            f"{name}是一种传统机器学习算法",
            f"{name}与深度学习无关",
        ]
        options = [f"A. {correct}（正确描述）", f"B. {distractors[0]}", f"C. {distractors[1]}", f"D. {distractors[2]}"]
        return {
            "type": "single",
            "stem": f"以下关于{name}的描述，哪个是正确的？",
            "options": options,
            "answer": "A",
            "explanation": f"{name}：{explanation[:200]}",
            "difficulty": difficulty,
            "source": f"出自{chapter_title}",
        }

    elif qtype == "multiple":
        correct = name
        return {
            "type": "multiple",
            "stem": f"关于{name}，以下哪些描述是正确的？（多选）",
            "options": [
                f"A. {explanation[:80]}",
                f"B. {name}是大模型技术体系中的重要组成部分",
                f"C. {name}仅在小规模数据上有效",
                f"D. 理解{name}有助于深入掌握大模型原理",
            ],
            "answer": "ABD",
            "explanation": f"A、B、D正确。{name}：{explanation[:200]}。选项C错误，因为{name}在大规模场景下同样适用。",
            "difficulty": difficulty,
            "source": f"出自{chapter_title}",
        }

    elif qtype == "judge":
        is_true = concept["is_key"] == 1
        return {
            "type": "judge",
            "stem": f"判断：{name}是人工智能领域的核心概念，{explanation[:100]}",
            "options": ["正确", "错误"],
            "answer": "正确" if is_true else "错误",
            "explanation": f"此陈述正确描述了{name}的基本特征。" if is_true else f"关于{name}的描述存在不准确之处。",
            "difficulty": difficulty,
            "source": f"出自{chapter_title}",
        }

    elif qtype == "short":
        return {
            "type": "short",
            "stem": f"请简述{name}的核心原理及其在大模型中的作用。",
            "options": [],
            "answer": explanation[:300],
            "explanation": f"考察对{name}的理解，要求能用自己的语言概括其核心机制和应用价值。",
            "difficulty": difficulty,
            "source": f"出自{chapter_title}",
        }

    elif qtype == "case":
        return {
            "type": "case",
            "stem": f"某科技公司正在开发一款AI产品，需要运用{name}技术。请分析：\n1. 该技术在产品中的具体应用方式\n2. 可能遇到的技术挑战\n3. 如何评估应用效果",
            "options": [],
            "answer": f"评分要点：\n1. 能准确描述{name}的技术原理\n2. 能结合具体场景分析应用方式\n3. 能识别潜在风险并提出应对方案",
            "explanation": f"案例分析题考察综合运用{name}知识解决实际问题的能力。",
            "difficulty": difficulty,
            "source": f"出自{chapter_title}",
        }

    return None
