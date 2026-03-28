# 🎯 HireSignal
### *Turn interview feedback into hiring intelligence*

HireSignal reads your interview notes and PDFs, and turns them into clear visual insights — who your best interviewers are, where your hiring bar sits, and why candidates pass or fail. No spreadsheets. No manual analysis. Just answers.

---

## ✨ What It Does

| Question | Where to find it |
|----------|-----------------|
| How different are our interviewers in style and strictness? | **Interview Team** page |
| Does our take-home predict how someone does in the tech interview? | **Insights** → Cross-Round Correlation |
| Where is our hiring bar? | **Insights** → Score by Round Type |
| What are the most common reasons candidates fail? | **Insights** → Positive & Negative Reasons |
| Ask anything about your hiring data | **Copilot** → AI Chat |

---

## 🚀 Getting Started

### What you need
- A Mac or Windows/Linux computer
- Python installed ([download here](https://www.python.org/downloads/) if you don't have it — get version 3.9 or newer)
- Your interview feedback as PDF files, text files, or CSV exports

> **That's it.** No accounts, no cloud setup, no API keys needed to get started.

---

### Step 1 — Download the app

Click the green **Code** button at the top of this page → **Download ZIP** → unzip it somewhere on your computer (e.g. your Desktop or Documents folder).

---

### Step 2 — Start the app

**On Mac:**
1. Open the Terminal app (search for "Terminal" in Spotlight)
2. Type `cd ` (with a space after), then drag the HireSignal folder into the Terminal window and press Enter
3. Type `./start.sh` and press Enter

**On Windows:**
1. Open the folder in File Explorer
2. Double-click `start.sh` (if you have Git Bash installed) or open Command Prompt, navigate to the folder, and run `python app.py`

The first time it runs, it will install a few things automatically — this takes about 1 minute. After that it opens in your browser automatically.

> 🌐 The app runs at **http://localhost:8021** — bookmark it!

---

### Step 3 — Add your feedback

1. Click **Add Feedback** in the left sidebar
2. Drag and drop your PDF files (interview scorecards, feedback exports) onto the upload area
3. Wait for the AI to read and structure the data — you'll see a live progress message
4. Once done, the dashboard populates automatically

**Supported formats:** PDF, plain text (.txt), CSV, JSON, Markdown

> ⏱️ A 10-page PDF takes about 1–2 minutes to process. Larger files take longer.

---

## 📖 Page Guide

### 🏠 Overview
Your hiring command center. See total candidates reviewed, pass rates, score trends over time, and which interviewers need attention.

### 👥 Interview Team
One card per interviewer. Shows their average score, pass rate, style tags (e.g. "detail-oriented", "big-picture"), and how they compare to each other. Use the **Compare** section at the bottom to put two interviewers side by side.

### 🔭 Role Pipelines
Breakdown by job role. See which pipelines are healthy (high pass rate, consistent scores) and which are problematic (low pass rate, lots of negative feedback).

### 💡 Insights
The most important page for answering leadership questions:
- **Top reasons** candidates pass or fail
- **Which reasons** actually correlate with hire/no-hire decisions
- **Score by round type** — how take-home, tech interview, and culture fit compare
- **Cross-round correlation** — does someone who does well in take-home also do well in the tech interview?

### 🤖 Copilot
Ask questions in plain English:
- *"Which interviewer is the strictest?"*
- *"What are the top reasons candidates fail the tech interview?"*
- *"Summarise the hiring trends from last month"*

You can also generate a **presentation deck** from the Copilot page — hit "Generate Deck" and it builds slides you can share with your team.

### ⚙️ Data Sources
Where your data comes from. Upload PDFs here, or connect to **Greenhouse ATS** (paste your API key to sync scorecards directly — or type `mock` to see a live demo).

---

## 🔌 Connecting to Greenhouse (Optional)

If your company uses Greenhouse for applicant tracking:

1. Go to **Data Sources** in the left sidebar
2. Under **Greenhouse ATS**, paste your Harvest API key
3. Click **Connect**
4. Data syncs automatically — no more manual exports

> Don't have an API key? Ask your Greenhouse admin. It's under *Configure → Dev Center → API Credential Management*.

---

## 🤖 AI Features

HireSignal uses AI to:
- Parse unstructured PDF feedback into structured data
- Answer questions about your hiring data in the Copilot
- Generate presentation decks

By default it uses **Claude Code** (Anthropic's AI CLI). If you have it installed, everything just works.

**Don't have Claude Code?** You can also use:
- **Codex CLI** (OpenAI)
- **Local models via Ollama** — runs 100% on your computer, no internet needed

Switch between them in **Data Sources → AI Backend**.

> 💡 If no AI is available, PDF uploads fall back to a simpler text parser — it still works, just less accurately.

---

## 📁 Your Data & Privacy

Everything stays on your computer. HireSignal does not send your feedback data to any server or cloud service. The only external calls are to the AI tool you choose (Claude/Codex) for parsing and answering questions — and even that can be replaced with a fully local Ollama model.

Data is stored in the `data/` folder inside the app directory:
- `data/uploads/` — your uploaded files
- `data/sessions/` — saved snapshots
- `data/decks/` — generated presentation decks

---

## 🛠️ Troubleshooting

**The app won't start**
- Make sure Python 3.9+ is installed: open Terminal and type `python3 --version`
- Try running `pip install -r requirements.txt` manually in the app folder

**PDF upload seems stuck**
- Large PDFs (10+ pages) can take 3–5 minutes with a local AI model
- Watch the status message on the Add Feedback page — it updates every few seconds
- If it fails, try splitting the PDF into smaller chunks

**The dashboard shows no data after upload**
- Click the reset button (↻) at the bottom of the sidebar and re-upload
- Check you're viewing "All datasets" in Data Sources

**Port 8021 already in use**
- Run `start.sh` again — it automatically stops the old instance and restarts

---

## 💻 For Developers

```bash
# Clone and run
git clone https://github.com/ranausmanai/hiresignal.git
cd hiresignal
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

**Stack:** Python 3.9+ · Flask · Chart.js 4.4 · Vanilla JS · Claude/Codex/Ollama for LLM

**Environment variables (all optional):**
```bash
INTERVIEW_INSIGHTS_LLM_BACKEND=claude     # claude | codex | ollama
INTERVIEW_INSIGHTS_CODEX_MODEL=gpt-5.3-codex
INTERVIEW_INSIGHTS_CODEX_REASONING=medium
INTERVIEW_INSIGHTS_OLLAMA_MODEL=qwen3.5:0.8b
FLASK_DEBUG=1                             # dev only
```

---

## 📄 License

MIT — free to use, modify, and share.

---

*Built for hiring teams who want signal, not noise.* 🎯
