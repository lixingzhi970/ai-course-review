"""扩展题库：每题型至少30道，满足任意组卷需求"""
import sys, os, json, random
sys.path.insert(0, os.path.dirname(__file__))
from database import get_db

type_names = {"single": "单选", "multiple": "多选", "judge": "判断", "short": "简答", "case": "案例分析"}
difficulties = ["基础", "中等", "挑战"]

concept_prompts = [
    ("请简述{n}的定义及其核心特征。", "short"),
    ("以下关于{n}的说法，哪个是正确的？", "single"),
    ("关于{n}，以下哪些是正确的？（多选）", "multiple"),
    ("判断：{n}是人工智能领域的核心概念之一。", "judge"),
    ("某公司开发AI产品时需要应用{n}技术，请分析其实现方案和潜在挑战。", "case"),
    ("{n}与深度学习中的其他机制相比有何独特之处？", "short"),
    ("在大模型时代，{n}的重要性体现在哪些方面？", "short"),
    ("以下哪个不是{n}的典型特征？", "single"),
    ("根据课程内容，{n}的局限性包括哪些？（多选）", "multiple"),
    ("判断：理解{n}对掌握大模型原理至关重要。", "judge"),
]

def generate_variants(concept, chapter_title, count_per_type=6):
    """Generate multiple question variants for a concept."""
    name = concept["name"]
    explanation = concept["explanation"]
    questions = []

    for i, (template, qtype) in enumerate(concept_prompts[:count_per_type]):
        stem = template.replace("{n}", name)

        if qtype == "single":
            options = [
                f"A. {explanation[:60]}",
                f"B. {name}仅是一种理论概念，无实际应用",
                f"C. {name}已被更先进的技术完全取代",
                f"D. {name}与人工智能领域无关",
            ]
            answer = "A"
        elif qtype == "multiple":
            options = [
                f"A. {name}是大模型技术体系的关键组成部分",
                f"B. {explanation[:60]}",
                f"C. {name}目前仅存在于理论研究中",
                f"D. 理解{n}有助于深入掌握AI技术原理",
            ]
            answer = "ABD"
        elif qtype == "judge":
            is_true = "关键" in explanation or "核心" in explanation or "基础" in explanation
            options = ["正确", "错误"]
            answer = "正确" if is_true else "错误"
        elif qtype == "short":
            options = []
            answer = f"核心要点：\n1. {name}：{explanation[:100]}\n2. 在大模型中的作用：{name}是实现大模型相关能力的基础组件\n3. 实际应用价值：为AI系统提供关键的技术支撑"
        elif qtype == "case":
            options = []
            answer = f"评分标准：\n1. 准确阐述{name}的技术原理（30%）\n2. 合理分析应用场景（30%）\n3. 识别潜在挑战并提出方案（40%）"

        difficulty = difficulties[i % 3]

        questions.append({
            "type": qtype,
            "stem": stem,
            "options": options,
            "answer": answer,
            "explanation": f"{name}：{explanation}",
            "chapter_id": concept["chapter_id"],
            "difficulty": difficulty,
            "source": f"出自{chapter_title}",
        })

    return questions


def expand():
    db = get_db()

    # Clear existing questions
    db.execute("DELETE FROM study_records")
    db.execute("DELETE FROM questions")
    db.commit()

    concepts = db.execute("SELECT c.*, ch.title as chapter_title FROM concepts c JOIN chapters ch ON c.chapter_id = ch.id").fetchall()

    total = 0
    for concept in concepts:
        variants = generate_variants(dict(concept), concept["chapter_title"], count_per_type=6)
        for q in variants:
            db.execute(
                """INSERT INTO questions (type, stem, options, answer, explanation, chapter_id, difficulty, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (q["type"], q["stem"], json.dumps(q["options"], ensure_ascii=False),
                 q["answer"], q["explanation"], q["chapter_id"],
                 q["difficulty"], q["source"]),
            )
            total += 1

    db.commit()

    # Show stats
    stats = db.execute("SELECT type, COUNT(*) as c FROM questions GROUP BY type ORDER BY type").fetchall()
    print(f"题库总数: {total}道")
    for s in stats:
        print(f"  {type_names.get(s['type'], s['type'])}: {s['c']}道")

    db.close()
    print("✅ 题库扩展完成！")


if __name__ == "__main__":
    expand()
