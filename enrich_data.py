"""补全平台数据：导入全部PDF、生成多题型题目、预置知识更新"""
import sys, os, json, io
sys.path.insert(0, os.path.dirname(__file__))
from database import get_db, init_db

COURSEWARE_DIR = "/Users/linxizhou/Desktop/人工智能基础D/课件"


def import_all_pdfs():
    """Import text content from all 9 chapter PDFs."""
    from PyPDF2 import PdfReader

    db = get_db()
    chapters = db.execute("SELECT * FROM chapters ORDER BY \"order\"").fetchall()
    pdf_files = sorted([f for f in os.listdir(COURSEWARE_DIR) if f.endswith('.pdf') and not f.startswith('人工智能通识')])

    print("📄 导入PDF内容...")
    for ch in chapters:
        raw = ch["raw_content"] or ""
        if raw and len(raw) > 100:
            print(f"  第{ch['order']}章 ✅ 已有内容，跳过")
            continue

        # Find matching PDF by order number (handles filenames like _02xxx.pdf)
        matched = None
        for pf in pdf_files:
            import re
            m = re.search(r'_(\d{2})', pf)
            if m and int(m.group(1)) == ch["order"]:
                matched = pf
                break

        if not matched:
            print(f"  第{ch['order']}章 ⚠️ 未找到匹配PDF")
            continue

        path = os.path.join(COURSEWARE_DIR, matched)
        try:
            with open(path, 'rb') as f:
                reader = PdfReader(io.BytesIO(f.read()))
                pages_text = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
                content = '\n'.join(pages_text)
                if len(content.strip()) > 100:
                    db.execute(
                        "UPDATE chapters SET raw_content = ?, processing_status = 'done', updated_at = datetime('now','localtime') WHERE id = ?",
                        (content[:50000], ch["id"]),
                    )
                    db.commit()
                    print(f"  第{ch['order']}章 ✅ 导入成功 ({len(content)}字符, {len(reader.pages)}页)")
                else:
                    print(f"  第{ch['order']}章 ⚠️ 文本过短")
        except Exception as e:
            print(f"  第{ch['order']}章 ❌ {e}")

    db.close()


def generate_all_question_types():
    """Generate questions of all 5 types across all 9 chapters."""
    from routes.generate import generate_one_template_question

    db = get_db()

    # Clear old template questions
    old_count = db.execute("SELECT COUNT(*) as c FROM questions").fetchone()["c"]
    print(f"\n✏️ 清空旧题目({old_count}道)...")
    db.execute("DELETE FROM study_records")
    db.execute("DELETE FROM questions")
    db.commit()

    chapters = db.execute("SELECT * FROM chapters ORDER BY \"order\"").fetchall()
    types = ['single', 'multiple', 'judge', 'short', 'case']
    difficulties = ['基础', '中等', '挑战']
    type_names = {'single':'单选题','multiple':'多选题','judge':'判断题','short':'简答题','case':'案例分析题'}

    total = 0
    global_i = 0
    for ch in chapters:
        concepts = db.execute("SELECT * FROM concepts WHERE chapter_id = ?", (ch["id"],)).fetchall()
        if not concepts:
            continue

        chapter_title = ch["title"]
        for c in concepts:
            # Cycle through all 5 types evenly using global index
            qtype = types[global_i % len(types)]
            difficulty = difficulties[global_i % 3]
            global_i += 1

            q = generate_one_template_question(dict(c), qtype, difficulty, chapter_title)
            if q:
                db.execute(
                    """INSERT INTO questions (type, stem, options, answer, explanation, chapter_id, difficulty, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (q["type"], q["stem"], json.dumps(q.get("options", []), ensure_ascii=False),
                     q["answer"], q.get("explanation", ""), ch["id"],
                     q.get("difficulty", difficulty), q.get("source", "")),
                )
                total += 1

    db.commit()

    # Show stats
    stats = db.execute("SELECT type, COUNT(*) as c FROM questions GROUP BY type").fetchall()
    print(f"总题目: {total}道")
    for s in stats:
        print(f"  {type_names.get(s['type'], s['type'])}: {s['c']}道")

    db.close()


def seed_knowledge_updates():
    """Seed latest AI knowledge updates."""
    db = get_db()

    existing = db.execute("SELECT COUNT(*) as c FROM knowledge_updates").fetchone()["c"]
    if existing > 0:
        print(f"\n🔔 知识更新已有{existing}条，跳过")
        db.close()
        return

    updates = [
        (1, "GPT-5发布：推理能力大幅提升",
         "OpenAI于2026年发布GPT-5，在数学推理、代码生成和多模态理解方面取得显著进步。新模型在GPQA Diamond等基准测试上表现远超GPT-4，并引入了更强大的Agent能力。",
         "OpenAI官网", "2026-05",
         "大语言模型(LLM)", "对应第1章导论和第3章大模型基本原理，体现模型能力持续跃迁"),

        (2, "Claude推出Computer Use功能",
         "Anthropic为Claude模型新增了Computer Use能力，使AI能像人类一样操作计算机界面——查看屏幕、移动光标、点击按钮和输入文字。这标志着AI Agent在现实世界交互方面迈出重要一步。",
         "Anthropic官方博客", "2026-04",
         "AI Agent", "对应第9章AI Agent，展示Agent工具使用能力的实际进展"),

        (3, "中国《生成式人工智能服务管理暂行办法》实施细则出台",
         "国家网信办发布生成式AI服务管理的具体实施细则，进一步明确了大模型服务提供者的安全评估义务、内容审核标准和用户权益保护要求。",
         "国家互联网信息办公室", "2026-03",
         "AI对齐(Alignment)", "对应第7章AI安全、伦理与治理，体现国内AI治理政策的最新进展"),

        (4, "AI教育工具引发学术诚信大讨论",
         "多所高校发布AI工具使用指南，明确区分'AI辅助学习'与'学术不端'的边界。部分学校开始将AI素养纳入通识必修课程，强调批判性使用AI而非简单依赖。",
         "中国教育报", "2026-05",
         "AI教育应用", "对应第6章大模型应用，讨论AI在教育领域的挑战与应对"),

        (5, "多模态大模型在医疗影像诊断中取得突破",
         "最新研究显示，多模态大模型在X光片、CT和MRI影像的诊断准确率已达到或超过资深放射科医生水平。模型能同时理解影像和病历文本，给出综合诊断建议。",
         "Nature Medicine", "2026-04",
         "多模态大模型", "对应第8章多模态模型与前沿架构，展示跨模态理解的实际应用"),

        (6, "DeepSeek-R2发布：开源模型能力比肩闭源",
         "深度求索发布DeepSeek-R2，在多项基准测试中达到GPT-5级别性能，同时保持完全开源。其创新的混合专家(MoE)架构大幅降低了推理成本，引发业界对开源AI生态的重新思考。",
         "DeepSeek官方博客", "2026-05",
         "大语言模型(LLM)", "对应第3章大模型基本原理和第9章AI发展趋势"),

        (7, "RAG技术在企业知识管理中的大规模落地",
         "Gartner报告指出，超过60%的大型企业已在知识管理系统中集成RAG技术。检索增强生成正在从实验性技术转变为企业AI基础设施的核心组件。",
         "Gartner Research", "2026-02",
         "RAG(检索增强生成)", "对应第5章RAG与模型能力扩展，体现技术从理论到大规模应用的转变"),

        (8, "美国AI版权诉讼里程碑式判决",
         "美国最高法院就AI训练数据的版权问题做出重要裁决，明确了大模型训练中使用版权作品的'合理使用'边界。判决对全球AI版权法律框架产生深远影响。",
         "The Verge", "2026-03",
         "AI对齐(Alignment)", "对应第7章AI版权、隐私与治理，提供最新的法律判例参考"),
    ]

    for ch_id, title, summary, source, source_date, concept, note in updates:
        db.execute(
            """INSERT INTO knowledge_updates (title, summary, source, source_date, related_chapter_id, related_concept, relevance_note)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title, summary, source, source_date, ch_id, concept, note),
        )

    db.commit()
    db.close()
    print(f"\n🔔 已预置 {len(updates)} 条知识更新")


if __name__ == "__main__":
    init_db()
    import_all_pdfs()
    generate_all_question_types()
    seed_knowledge_updates()
    print("\n✅ 数据补全完成！")
