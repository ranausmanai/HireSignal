# 📊 Interview Insights

**Visual feedback analyzer for engineering hiring teams.**

Ingest interview feedback from text files, CSVs, or pasted text — and instantly see beautiful, interactive dashboards that reveal calibration gaps, interviewer biases, and hiring inconsistencies.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/flask-2.3%2B-000?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Chart.js](https://img.shields.io/badge/chart.js-4.x-ff6384?logo=chartdotjs&logoColor=white)](https://www.chartjs.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 📸 Screenshots

> *Dashboard loads instantly with 50 sample feedback entries — all charts populated out of the box.*

| Dashboard | Upload |
|-----------|--------|
| ![Dashboard](https://via.placeholder.com/600x400/0a0a0f/4f8fff?text=Dashboard) | ![Upload](https://via.placeholder.com/600x400/0a0a0f/4f8fff?text=Upload+%26+Paste) |

---

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/your-org/interview-insights.git
cd interview-insights

# Install dependencies
pip install -r requirements.txt

# Run the server
python3 app.py

# Open in browser
open http://localhost:8000
```

That's it. The app loads with built-in sample data — all charts are live immediately.

---

## ✨ Features

### 📥 Feedback Ingestion
- **Drag & drop** `.txt`, `.csv`, `.json`, `.md` files
- **Paste mode** for quick text input
- Smart parsing extracts interviewer, candidate, role, decision, score, themes, sentiment, and date
- Handles diverse formats with fuzzy column matching and regex extraction

### 📊 Interactive Dashboard
- **Interviewer Calibration Heatmap** — Spot who's too harsh or too lenient, broken down by role
- **Decision Distribution** — Stacked bar chart showing hire/no-hire/maybe breakdown per role
- **Interviewer Agreement Matrix** — Pairwise agreement rates when two interviewers evaluate the same candidate
- **Score Distribution** — Grouped bar chart revealing each interviewer's scoring patterns
- **Theme Frequency Radar** — Spider chart of evaluation themes (technical, communication, culture fit, etc.)
- **Sentiment Over Time** — Monthly sentiment trend line with gradient fill
- **Consistency Gauge** — The centerpiece: a 0-100 score for how calibrated your hiring bar is
- **Word Cloud** — Most frequent feedback terms, sized by frequency
- **Red Flags Panel** — Auto-detected calibration concerns with severity ratings

### 🔍 Drill-down & Filtering
- Filter all charts by role, interviewer, date range, or decision outcome
- Click any data point to see the actual feedback entries behind it
- Compare two interviewers side-by-side on the Interviewers page

### 📋 Executive Summary
- Auto-generated summary with key stats and top 3 actionable insights
- No external APIs — all analysis runs locally with heuristics

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Browser (SPA)                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ app.js   │  │ charts.js│  │   Chart.js (CDN)  │  │
│  │ routing, │  │ 9 chart  │  │   rendering       │  │
│  │ upload,  │  │ renderers│  │   engine           │  │
│  │ filters  │  │          │  │                    │  │
│  └────┬─────┘  └──────────┘  └───────────────────┘  │
│       │                                              │
│       │  fetch /api/data, /api/upload, /api/paste    │
└───────┼──────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────┐
│                Flask Server (app.py)               │
│                                                    │
│  ┌────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │  Parsers   │  │  Analytics  │  │  In-Memory │  │
│  │  CSV/JSON/ │──▶  Engine     │──▶  Store +   │  │
│  │  TXT/MD    │  │  (compute)  │  │  sample.json│  │
│  └────────────┘  └─────────────┘  └────────────┘  │
│                                                    │
│  Parsers:         Analytics:                       │
│  • Fuzzy CSV      • Per-interviewer stats          │
│    column match   • Agreement matrix               │
│  • Flexible JSON  • Consistency score (0-100)      │
│    field mapping  • Red flag detection             │
│  • Regex text     • Theme frequencies              │
│    extraction     • Sentiment timeline             │
│  • Keyword-based  • Word frequencies               │
│    theme detect   • Executive summary generation   │
└───────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
interview-insights/
├── app.py                  # Flask server, API routes, parsers, analytics
├── requirements.txt        # Python dependencies (Flask)
├── templates/
│   └── index.html          # SPA shell with sidebar, pages, modal
├── static/
│   ├── css/
│   │   └── style.css       # Dark theme (Grafana-meets-Linear aesthetic)
│   └── js/
│       ├── app.js          # Page routing, uploads, filters, data fetching
│       └── charts.js       # 9 chart rendering functions
├── data/
│   └── sample.json         # 50 pre-loaded interview feedback entries
└── README.md
```

---

## 📄 Supported Input Formats

| Format | How it's parsed |
|--------|----------------|
| **CSV** | Auto-detects columns by fuzzy header matching (interviewer, candidate, role, score, etc.) |
| **JSON** | Accepts arrays of objects with flexible field names |
| **TXT/MD** | Regex extraction for labeled fields (`Interviewer:`, `Score:`, etc.) and keyword-based theme/decision detection |

---

## 🎨 Design

- **Dark theme**: `#0a0a0f` background, `#12121a` cards, subtle `#1a1a2e` borders
- **Accent palette**: Blue `#4f8fff`, Green `#34d399`, Red `#ef4444`, Yellow `#fbbf24`, Purple `#a78bfa`
- **Typography**: System font stack, large bold KPI numbers, uppercase chart labels
- **Animations**: 800ms chart transitions, hover lift on cards, pulsing upload border
- **Responsive**: 2-column grid on desktop, single column on mobile, collapsible sidebar

---

## 🧪 Sample Data

The included `data/sample.json` contains 50 realistic feedback entries with:
- **8 interviewers** with distinct calibration patterns (Sarah Chen is tough, Mike Johnson is lenient)
- **25 candidates** across 5 roles
- **Deliberate disagreements** between interviewer pairs for interesting agreement matrices
- **Varied scores, themes, and sentiments** spread across 12 months

---

## 📝 License

MIT
