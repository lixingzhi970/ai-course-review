# AI课程期末复习平台

面向《人工智能通识基础（大模型篇）》的期末复习系统。支持课程知识库管理、学习目标对齐、自动出题、复习辅助和最新知识更新。

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库
python3 seed_data.py

# 3. 启动服务
python3 main.py

# 4. 打开浏览器访问
# http://localhost:3000
```

## 功能模块

### 1. 课程知识库 (/knowledge)
- 9个章节的知识结构浏览
- 核心概念解释（含难度标注、重点标记）
- 学习目标对齐表
- 概念关系图谱（D3.js可视化）
- 章节题目预览

### 2. 学习目标对齐 (/objectives)
- 课程内容 → 学习目标 → 应掌握什么 → 考查方式的全对齐表
- 辅助学生明确每章重点和考试方向

### 3. 自动出题 (/practice)
- 5种题型：单选题、多选题、判断题、简答题、案例分析题
- 按章节/题型/难度筛选练习
- AI智能出题（需配置AI_API_KEY环境变量）
- 模板出题（无需API Key即可使用）
- 答题即时反馈 + 详细解析
- 答题记录追踪

### 4. 复习辅助 (/review)
- 章节摘要：按章节查看核心概念和学习目标检查清单
- 概念卡片：翻转式记忆工具
- 错题本：自动记录错题，分析薄弱章节，推荐复习内容
- 自测模式：随机出题练习

### 5. 最新知识更新 (/updates)
- 添加最新AI案例、新闻、技术进展
- 标明来源、日期
- 关联课程章节和概念
- 说明与课程知识点的关联

### 6. 数据导入 (/import)
- 上传课件PDF
- 自动文本提取
- AI辅助内容解析
- 课件目录浏览

## 配置AI智能出题

```bash
# 设置环境变量启用AI出题
export AI_API_KEY="your-api-key-here"
export AI_API_BASE="https://api.anthropic.com"  # 或 OpenAI API
export AI_MODEL="claude-sonnet-4-6"

# 然后启动
python3 main.py
```

不配置API Key时，系统使用模板自动生成题目，同样包含完整的题干、答案和解析。

## 项目结构

```
ai-course-review/
├── main.py                 # FastAPI主入口
├── database.py             # SQLite数据库
├── seed_data.py            # 种子数据（9章课程结构）
├── requirements.txt        # Python依赖
├── routes/                 # API路由
│   ├── chapters.py         # 知识库
│   ├── objectives.py       # 学习目标
│   ├── questions.py        # 练习与答题
│   ├── review.py           # 复习辅助
│   ├── updates.py          # 知识更新
│   ├── import_data.py      # 数据导入
│   └── generate.py         # AI出题
├── templates/              # Jinja2模板
│   ├── base.html           # 基础布局
│   ├── index.html          # 仪表盘
│   ├── knowledge/          # 知识库页面
│   ├── objectives/         # 学习目标页面
│   ├── practice/           # 练习页面
│   ├── review/             # 复习页面
│   ├── updates/            # 更新页面
│   └── import/             # 导入页面
└── data/
    └── course.db           # SQLite数据库文件
```

## 课程内容

平台预置9章课程内容结构：

1. 导论：走进人工智能与大模型时代
2. 通用人工智能：从专用到通用的演进
3. 大模型基本原理
4. 提示词工程与模型交互
5. 检索增强生成(RAG)与模型能力扩展
6. 大模型应用与实践
7. AI安全、伦理与治理
8. 多模态模型与前沿架构
9. AI Agent与未来发展

每章包含学习目标、核心概念（共26个）和题目生成能力。

## 课件导入

课件PDF位置：`/Users/linxizhou/Desktop/人工智能基础D/课件/`

在数据导入页面选择对应章节，上传PDF文件即可将内容导入平台。
