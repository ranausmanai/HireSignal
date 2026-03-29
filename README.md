<p align="center">
  <img src="static/favicon.svg" width="80" alt="HireSignal Logo" />
</p>

<h1 align="center">🎯 HireSignal</h1>

<p align="center">
  <strong>Turn interview feedback into hiring intelligence</strong><br/>
  <em>Built for recruiters. Powered by AI. Runs on your laptop.</em>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> ·
  <a href="#-features">Features</a> ·
  <a href="#-complete-installation-guide">Installation</a> ·
  <a href="#-page-by-page-guide">Page Guide</a> ·
  <a href="#-for-developers">Developer Docs</a>
</p>

---

## 🧐 What is HireSignal?

HireSignal is a tool that **reads your interview feedback** — PDFs, exported notes, pasted text, or Greenhouse scorecards — and gives you **clear, visual answers** to the questions hiring managers actually ask:

> *"Are our interviewers calibrated?"*
> *"What's our hiring bar?"*
> *"Why are candidates failing?"*

You drop in your feedback files, and HireSignal does the rest — no spreadsheets, no manual tagging, no data cleanup.

### 🔒 Privacy First
Everything runs **locally on your computer**. Your candidate data never leaves your machine. No cloud accounts needed.

---

## ⚡ Quick Start

If you just want to get it running (details below):

```bash
git clone https://github.com/ranausmanai/HireSignal.git
cd HireSignal
./start.sh
```

That's it. It installs everything, opens your browser, and you're ready to upload feedback.

---

## ✨ Features

### 📊 Six Pages of Insight

| Page | What you get |
|------|-------------|
| 🏠 **Overview** | Hiring command center — pass rates, score trends, candidates needing attention |
| 📄 **Add Feedback** | Drop PDFs or paste raw notes — AI structures them automatically |
| 👥 **Interview Team** | Per-interviewer cards with style tags, score patterns, side-by-side comparison |
| 🔭 **Role Pipelines** | Health check per job role — pass rates, blockers, pipeline friction |
| 💡 **Insights** | Cross-round correlation, reason analysis, hiring bar visualization |
| 🤖 **Copilot** | Ask questions in English, generate shareable slide decks |

### 🧠 AI-Powered

- 📝 **PDF Parsing** — Drop a 10-page feedback PDF, get structured data in 1–2 minutes
- 💬 **Copilot Chat** — Ask *"Who is our strictest interviewer?"* and get a real answer
- 📊 **Deck Generator** — Create leadership briefing slides with one click
- 🔄 **3 AI backends** — Claude Code, Codex CLI, or fully local via Ollama (no internet)

### 🔌 Data Sources

- **PDF / Text / CSV / JSON** — upload anything, AI figures out the structure
- **Greenhouse ATS** — connect with your Harvest API key to sync scorecards directly
- **Mock data** — type `mock` in the Greenhouse field to explore with sample data

---

## 📦 Complete Installation Guide

### Prerequisites

You need **one thing**: Python 3.9 or newer.

<details>
<summary>🍎 <strong>How to check if you have Python (Mac)</strong></summary>

1. Press `Cmd + Space` to open Spotlight
2. Type **Terminal** and press Enter
3. In the Terminal window, type this and press Enter:
   ```
   python3 --version
   ```
4. If you see something like `Python 3.11.5` — you're good! Skip to the next section.
5. If you see `command not found` — you need to install Python:
   - Go to [python.org/downloads](https://www.python.org/downloads/)
   - Click the big yellow **Download Python** button
   - Open the downloaded file and follow the installer
   - When it's done, **close Terminal and reopen it**, then try `python3 --version` again

</details>

<details>
<summary>🪟 <strong>How to check if you have Python (Windows)</strong></summary>

1. Press `Win + R`, type `cmd`, press Enter
2. Type this and press Enter:
   ```
   python --version
   ```
3. If you see `Python 3.x.x` — you're good!
4. If not:
   - Go to [python.org/downloads](https://www.python.org/downloads/)
   - Download and run the installer
   - ⚠️ **IMPORTANT:** Check the box that says **"Add Python to PATH"** during installation
   - Close and reopen Command Prompt, try `python --version` again

</details>

---

### Option A — Download as ZIP (easiest, no git needed)

1. Click the green **< > Code** button at the top of this GitHub page
2. Click **Download ZIP**
3. Unzip the downloaded file — you'll get a folder called `HireSignal-main`
4. Move it somewhere convenient (Desktop, Documents, etc.)

Now follow the **"Running the App"** section below.

---

### Option B — Clone with Git (for developers)

```bash
git clone https://github.com/ranausmanai/HireSignal.git
cd HireSignal
```

---

### Running the App

#### 🍎 Mac / 🐧 Linux

1. Open **Terminal**
2. Navigate to the HireSignal folder. The easiest way:
   - Type `cd ` (with a space after the `cd`)
   - **Drag the HireSignal folder** from Finder into the Terminal window
   - Press **Enter**
3. Run the start script:
   ```bash
   ./start.sh
   ```
4. The script will:
   - ✅ Check your Python version
   - ✅ Create a virtual environment (first time only)
   - ✅ Install all dependencies (first time only)
   - ✅ Start the app
   - ✅ Open your browser automatically

> 💡 **First run** takes about 60 seconds (downloading dependencies). After that, it starts in ~3 seconds.

#### 🪟 Windows

1. Open **Command Prompt** (press `Win + R`, type `cmd`, press Enter)
2. Navigate to the HireSignal folder:
   ```
   cd C:\Users\YourName\Desktop\HireSignal-main
   ```
   (Replace with the actual path to where you put the folder)
3. Set up the environment (first time only):
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. Start the app:
   ```
   python app.py
   ```
5. Open your browser and go to **http://localhost:8021**

---

### 🎉 You should see...

Your browser opens to **http://localhost:8021** with a dark-themed dashboard. The sidebar on the left has all the pages. The first time, the dashboard will be empty — that's normal! You need to upload your feedback data first.

To stop the app, go back to Terminal and press **Ctrl + C**.

---

## 📖 Page-by-Page Guide

### 🏠 Overview

The landing page. Shows:
- **Total candidates** reviewed and overall pass rate
- **Score distribution** — how scores spread across 1–5
- **Timeline** — trends over time
- **Attention alerts** — interviewers or candidates that need review

> 💡 This is your "glance at the morning" page.

---

### 📄 Add Feedback

This is where data gets into HireSignal.

**To upload files:**
1. Click **Add Feedback** in the sidebar
2. Drag and drop your files onto the upload area (or click to browse)
3. A progress message appears: *"AI is reading the PDF — this takes 1–2 minutes…"*
4. When done, it says *"Done — 28 entries added"*
5. Go to **Overview** — your dashboard is now populated

**Supported file types:** `.pdf` `.txt` `.csv` `.json` `.md`

**To paste raw text:**
1. Click the **Paste Text** tab
2. Paste your interview notes directly
3. Click **Submit Feedback**

> ⏱️ **Speed guide:** A 5-page PDF takes ~1 minute with Claude, ~3 minutes with a local Ollama model.

---

### 👥 Interview Team

One card for each interviewer showing:
- 📊 **Average score** they give (are they harsh or lenient?)
- ✅ **Pass rate** (what percentage of their candidates pass?)
- 🏷️ **Style tags** — automatically detected (e.g. "detail-oriented", "values communication")
- 📋 **Top reasons** they cite in positive and negative feedback

**Compare mode:** Scroll to the bottom, pick two interviewers from the dropdowns, and see them side by side — useful for calibration discussions.

---

### 🔭 Role Pipelines

Grouped by job role (e.g. "PHP Developer", "Senior PHP Developer"):
- Which roles have healthy pipelines (good pass rate, consistent scores)
- Which roles have friction (high rejection, repeated issues)
- The most common feedback themes per role

---

### 💡 Insights

The deepest page. Answers leadership questions directly:

**📌 Top Positive & Negative Reasons**
What comes up most often in positive feedback ("strong technical knowledge") and negative feedback ("gaps in fundamentals").

**📌 Reason Impact**
Which specific reasons actually correlate with hire vs. no-hire decisions — not just frequency, but impact.

**📌 Score by Round Type**
Average scores and pass rates for each interview round type (take-home, tech interview, culture fit, etc.). Shows where the **hiring bar** sits per round.

**📌 Cross-Round Correlation** *(the big one)*
A matrix showing each candidate's score and decision across different round types. If someone scores a 5 on the take-home but a 2 in the tech interview, that row lights up red. Shows whether your rounds are aligned or contradicting each other.

**📌 Round Pair Summary**
Agreement rates between pairs of round types. *"Take-home and tech interview agree 60% of the time across 5 shared candidates."*

---

### 🤖 Copilot

Two features in one page:

**💬 Chat**
Type any question in plain English:
- *"Which interviewer is the strictest?"*
- *"What are the top 3 reasons candidates fail?"*
- *"Compare Jan's feedback style to Ondrej's"*
- *"What does the data say about our hiring bar?"*

The AI has full context of all your uploaded data.

**📊 Deck Generator**
Click **Generate Deck** to create a presentation-ready HTML slide deck. Great for sharing with leadership. Choose a topic (e.g. *"Interviewer Calibration Brief"*) and it generates a complete deck with charts and findings.

Generated decks are saved and can be accessed later from the deck library.

---

### ⚙️ Data Sources

Three sections:

**1. Source Cards** — PDF Upload (links to Add Feedback page) and Greenhouse ATS (enter API key to connect)

**2. AI Backend** — Switch between:
- ⚡ **Claude Code** — fastest and most accurate (needs [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed)
- 🚀 **Codex CLI** — OpenAI alternative
- 🏠 **Local (Ollama)** — fully offline, runs on your machine (needs [Ollama](https://ollama.com/) installed)

**3. Your Datasets** — Manage uploaded datasets, compare them, delete old ones

---

## 🔌 Greenhouse ATS Integration

If your company uses Greenhouse:

1. Get your **Harvest API key** from Greenhouse:
   - Go to Greenhouse → *Configure* → *Dev Center* → *API Credential Management*
   - Create a new key with **Harvest** permissions
2. In HireSignal, go to **Data Sources**
3. Paste the key under **Greenhouse ATS** → click **Connect**
4. Click **Sync Latest** to pull in new scorecards

> 🧪 **Want to try it first?** Type `mock` as the API key to load sample Greenhouse data.

---

## 🛠️ Troubleshooting

<details>
<summary><strong>❌ "Python is not installed" or "command not found"</strong></summary>

Download Python 3.9+ from [python.org/downloads](https://www.python.org/downloads/). On Windows, make sure to check **"Add Python to PATH"** during installation. After installing, close and reopen your terminal.
</details>

<details>
<summary><strong>❌ "./start.sh: Permission denied"</strong></summary>

Run this once:
```bash
chmod +x start.sh
./start.sh
```
</details>

<details>
<summary><strong>❌ PDF upload says "Processing" but nothing happens</strong></summary>

- Check which AI backend is active (bottom-left of sidebar). If it says "Not found", you need to install Claude Code, Codex, or Ollama.
- Try switching to a different backend in Data Sources → AI Backend.
- Large PDFs (10+ pages) take 3–5 minutes — watch the status message, it updates every 2 seconds.
</details>

<details>
<summary><strong>❌ Dashboard is empty after uploading</strong></summary>

- Click the ↻ reset button at the bottom of the sidebar, then re-upload
- Make sure you're on the correct dataset in Data Sources
</details>

<details>
<summary><strong>❌ "Port 8021 already in use"</strong></summary>

Run `./start.sh` again — it automatically kills the old process. Or manually:
```bash
lsof -ti:8021 | xargs kill
python app.py
```
</details>

<details>
<summary><strong>❌ Copilot / Chat is not responding</strong></summary>

Copilot needs an AI backend. Check:
- Is Claude Code installed? Run `claude --version` in Terminal
- Or switch to Ollama: install from [ollama.com](https://ollama.com/), run `ollama pull qwen3.5:0.8b`, then switch backend in Data Sources
</details>

---

## 💻 For Developers

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.9+ · Flask |
| Frontend | Vanilla JS · Chart.js 4.4 |
| AI | Claude Code CLI · Codex CLI · Ollama (local) |
| Data | In-memory (JSON persistence for sessions) |
| ATS | Greenhouse Harvest API (real + mock) |

### Project Structure

```
HireSignal/
├── app.py                 # Flask backend (routes, analytics, LLM integration)
├── mock_greenhouse.py     # Mock Greenhouse API data for demos
├── start.sh               # One-click launcher (venv + deps + server)
├── requirements.txt       # Python dependencies
├── static/
│   ├── favicon.svg        # App icon
│   ├── css/style.css      # Full dark-theme stylesheet
│   └── js/
│       ├── app.js         # SPA logic, page rendering, API calls
│       └── charts.js      # Chart.js configuration and chart builders
├── templates/
│   └── index.html         # Single-page app shell
└── data/
    ├── uploads/           # User-uploaded PDFs and files
    ├── sessions/          # Saved data snapshots
    └── decks/             # Generated HTML presentation decks
```

### Quick Dev Setup

```bash
git clone https://github.com/ranausmanai/HireSignal.git
cd HireSignal
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                    # → http://localhost:8021
```

### Environment Variables

All optional. Set before running `python app.py`:

| Variable | Default | Options |
|----------|---------|---------|
| `INTERVIEW_INSIGHTS_LLM_BACKEND` | `claude` | `claude` · `codex` · `ollama` |
| `INTERVIEW_INSIGHTS_CODEX_MODEL` | `gpt-5.3-codex` | Any Codex model name |
| `INTERVIEW_INSIGHTS_CODEX_REASONING` | `medium` | `low` · `medium` · `high` |
| `INTERVIEW_INSIGHTS_OLLAMA_MODEL` | `qwen3.5:0.8b` | Any Ollama model tag |
| `FLASK_DEBUG` | *(off)* | `1` to enable |

### Key API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/data` | All entries + computed analytics |
| POST | `/api/upload` | Upload files (returns job ID for async PDF processing) |
| GET | `/api/upload/status/<id>` | Poll PDF parsing progress |
| POST | `/api/chat` | Copilot chat |
| POST | `/api/deck` | Generate presentation deck |
| GET | `/api/llm/status` | Current AI backend + availability |
| POST | `/api/llm/set` | Switch AI backend |
| POST | `/api/greenhouse/connect` | Connect Greenhouse API |

---

## 📄 License

MIT — free to use, modify, and share.

---

<p align="center">
  <em>Built for hiring teams who want signal, not noise.</em> 🎯
</p>
