"""Interview Insights — Visual Feedback Analyzer for Engineering Hiring Teams."""

import csv
import io
import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# In-memory feedback store
feedback_store = []

# Theme keyword mappings for extraction
THEME_KEYWORDS = {
    "technical_skills": ["technical", "algorithm", "data structure", "architecture", "api", "database",
                         "infrastructure", "framework", "language", "stack", "engineering", "design pattern"],
    "communication": ["communicat", "articulate", "explain", "clarity", "verbal", "written",
                      "present", "collaborate", "listen", "express"],
    "culture_fit": ["culture", "team", "values", "mindset", "attitude", "personality",
                    "collaborative", "fit", "energy", "vibe"],
    "problem_solving": ["problem.solv", "debug", "troubleshoot", "approach", "analytical",
                        "creative", "solution", "logic", "reasoning", "methodology"],
    "leadership": ["leader", "mentor", "manage", "guide", "initiative", "ownership",
                   "influence", "decision.mak", "strategic", "vision"],
    "system_design": ["system design", "architect", "scalab", "distributed", "microservice",
                      "caching", "load balanc", "trade.off", "high.availability"],
    "coding_ability": ["cod", "implement", "syntax", "clean code", "refactor", "test",
                       "debug", "programming", "software", "build"],
}

POSITIVE_WORDS = {"excellent", "outstanding", "strong", "great", "impressive", "exceptional",
                  "fantastic", "solid", "talented", "brilliant", "amazing", "recommend",
                  "hire", "confident", "thorough", "elegant", "clean", "deep", "clear",
                  "thoughtful", "creative", "innovative", "remarkable", "superb", "perfect"}

NEGATIVE_WORDS = {"weak", "poor", "lacking", "struggled", "couldn't", "unable", "limited",
                  "concerned", "concerning", "gap", "gaps", "below", "insufficient", "miss",
                  "missing", "fail", "failed", "reject", "shallow", "superficial", "naive",
                  "minimal", "basic", "fundamental", "inadequate", "disappointing"}

DECISION_MAP = {
    "strong_hire": "strong_hire", "strong hire": "strong_hire", "strongly hire": "strong_hire",
    "hire": "hire", "yes": "hire", "pass": "hire", "accept": "hire", "recommend": "hire",
    "maybe": "maybe", "lean hire": "maybe", "lean no": "maybe", "borderline": "maybe",
    "on the fence": "maybe", "undecided": "maybe",
    "no_hire": "no_hire", "no hire": "no_hire", "no": "no_hire", "reject": "no_hire",
    "fail": "no_hire", "decline": "no_hire", "not recommended": "no_hire",
    "strong_no_hire": "strong_no_hire", "strong no hire": "strong_no_hire",
    "strong reject": "strong_no_hire", "absolutely not": "strong_no_hire",
}


def load_sample_data():
    """Load sample data from JSON file."""
    sample_path = os.path.join(os.path.dirname(__file__), "data", "sample.json")
    with open(sample_path, "r") as f:
        return json.load(f)


def extract_themes(text):
    """Extract themes from feedback text using keyword matching."""
    text_lower = text.lower()
    themes = []
    for theme, keywords in THEME_KEYWORDS.items():
        for kw in keywords:
            if re.search(kw, text_lower):
                themes.append(theme)
                break
    return themes if themes else ["technical_skills"]


def compute_sentiment(text):
    """Compute sentiment score from text using word lists."""
    words = set(re.findall(r'\b\w+\b', text.lower()))
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 2)


def extract_decision(text):
    """Extract hiring decision from text."""
    text_lower = text.lower()
    for phrase, decision in sorted(DECISION_MAP.items(), key=lambda x: -len(x[0])):
        if phrase in text_lower:
            return decision
    return "maybe"


def extract_score(text):
    """Extract numeric score from text."""
    # Look for patterns like "4/5", "3 out of 5", "score: 4", "rating: 3"
    patterns = [
        r'(\d)\s*/\s*5', r'(\d)\s+out\s+of\s+5', r'score[:\s]+(\d)',
        r'rating[:\s]+(\d)', r'\b([1-5])\b.*(?:star|point|score)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            score = int(match.group(1))
            if 1 <= score <= 5:
                return score
    return 3  # default


def extract_date(text):
    """Extract date from text."""
    patterns = [
        (r'(\d{4}-\d{2}-\d{2})', "%Y-%m-%d"),
        (r'(\d{2}/\d{2}/\d{4})', "%m/%d/%Y"),
        (r'(\d{2}-\d{2}-\d{4})', "%m-%d-%Y"),
    ]
    for pattern, fmt in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return datetime.strptime(match.group(1), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return datetime.now().strftime("%Y-%m-%d")


def extract_field(text, labels):
    """Extract a labeled field value from text."""
    for label in labels:
        match = re.search(rf'{label}[:\s]+([^\n,;]+)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def parse_text_feedback(text):
    """Parse a single text/markdown feedback entry."""
    interviewer = extract_field(text, ["interviewer", "reviewed by", "evaluator", "assessor"]) or "Unknown"
    candidate = extract_field(text, ["candidate", "applicant", "interviewee", "name"]) or "Unknown"
    role = extract_field(text, ["role", "position", "job", "title"]) or "Unknown"
    return {
        "id": None,
        "interviewer": interviewer,
        "candidate": candidate,
        "role": role,
        "decision": extract_decision(text),
        "score": extract_score(text),
        "themes": extract_themes(text),
        "sentiment": compute_sentiment(text),
        "date": extract_date(text),
        "feedback_text": text.strip()[:2000],
    }


def parse_csv_feedback(content):
    """Parse CSV content into feedback entries."""
    reader = csv.DictReader(io.StringIO(content))
    entries = []
    # Build a fuzzy column map
    col_map = {}
    if reader.fieldnames:
        for field in reader.fieldnames:
            fl = field.lower().strip()
            if any(k in fl for k in ["interviewer", "reviewer", "evaluator"]):
                col_map["interviewer"] = field
            elif any(k in fl for k in ["candidate", "applicant", "name"]):
                col_map["candidate"] = field
            elif any(k in fl for k in ["role", "position", "title", "job"]):
                col_map["role"] = field
            elif any(k in fl for k in ["decision", "outcome", "result", "verdict"]):
                col_map["decision"] = field
            elif any(k in fl for k in ["score", "rating", "grade"]):
                col_map["score"] = field
            elif any(k in fl for k in ["feedback", "comments", "notes", "text"]):
                col_map["feedback"] = field
            elif any(k in fl for k in ["date", "time", "when"]):
                col_map["date"] = field
            elif any(k in fl for k in ["theme", "signal", "skill"]):
                col_map["themes"] = field

    for row in reader:
        text = row.get(col_map.get("feedback", ""), "")
        score_raw = row.get(col_map.get("score", ""), "")
        try:
            score = int(float(score_raw))
            score = max(1, min(5, score))
        except (ValueError, TypeError):
            score = extract_score(text) if text else 3

        decision_raw = row.get(col_map.get("decision", ""), "")
        decision = DECISION_MAP.get(decision_raw.lower().strip(), extract_decision(text) if text else "maybe")

        date_raw = row.get(col_map.get("date", ""), "")
        date = extract_date(date_raw) if date_raw else extract_date(text) if text else datetime.now().strftime("%Y-%m-%d")

        themes_raw = row.get(col_map.get("themes", ""), "")
        if themes_raw:
            themes = [t.strip() for t in themes_raw.split(",")]
        else:
            themes = extract_themes(text) if text else ["technical_skills"]

        entries.append({
            "id": None,
            "interviewer": row.get(col_map.get("interviewer", ""), "Unknown").strip() or "Unknown",
            "candidate": row.get(col_map.get("candidate", ""), "Unknown").strip() or "Unknown",
            "role": row.get(col_map.get("role", ""), "Unknown").strip() or "Unknown",
            "decision": decision,
            "score": score,
            "themes": themes,
            "sentiment": compute_sentiment(text) if text else 0.0,
            "date": date,
            "feedback_text": (text or f"CSV entry: {json.dumps(row)}")[:2000],
        })
    return entries


def parse_json_feedback(content):
    """Parse JSON content into feedback entries."""
    data = json.loads(content)
    if isinstance(data, dict):
        data = [data]
    entries = []
    for item in data:
        text = item.get("feedback_text", item.get("feedback", item.get("comments", item.get("notes", ""))))
        themes = item.get("themes", [])
        if isinstance(themes, str):
            themes = [t.strip() for t in themes.split(",")]
        if not themes:
            themes = extract_themes(text) if text else ["technical_skills"]

        score = item.get("score", item.get("rating", None))
        if score is not None:
            try:
                score = max(1, min(5, int(float(score))))
            except (ValueError, TypeError):
                score = extract_score(text) if text else 3
        else:
            score = extract_score(text) if text else 3

        decision = item.get("decision", item.get("outcome", item.get("result", "")))
        decision = DECISION_MAP.get(str(decision).lower().strip(), extract_decision(text) if text else "maybe")

        entries.append({
            "id": item.get("id"),
            "interviewer": item.get("interviewer", item.get("reviewer", "Unknown")),
            "candidate": item.get("candidate", item.get("applicant", "Unknown")),
            "role": item.get("role", item.get("position", "Unknown")),
            "decision": decision,
            "score": score,
            "themes": themes,
            "sentiment": item.get("sentiment", compute_sentiment(text) if text else 0.0),
            "date": item.get("date", extract_date(text) if text else datetime.now().strftime("%Y-%m-%d")),
            "feedback_text": (text or json.dumps(item))[:2000],
        })
    return entries


def parse_file(filename, content):
    """Route file to appropriate parser based on extension."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".csv":
        return parse_csv_feedback(content)
    elif ext == ".json":
        return parse_json_feedback(content)
    else:
        # Text or markdown — split on double newlines for multiple entries
        blocks = re.split(r'\n{2,}---\n{2,}|\n{3,}', content)
        entries = []
        for block in blocks:
            block = block.strip()
            if len(block) > 20:
                entries.append(parse_text_feedback(block))
        return entries if entries else [parse_text_feedback(content)]


def assign_ids(entries):
    """Assign unique IDs to entries that don't have one."""
    max_id = max((e.get("id") or 0 for e in feedback_store), default=0)
    for entry in entries:
        if not entry.get("id"):
            max_id += 1
            entry["id"] = max_id


def compute_analytics(data):
    """Compute all analytics from feedback data."""
    if not data:
        return {
            "entries": [], "per_interviewer": {}, "per_role": {},
            "agreement_matrix": {}, "consistency_score": 0,
            "theme_frequencies": {}, "sentiment_timeline": {},
            "red_flags": [], "executive_summary": "No data available.",
            "top_insights": [], "word_frequencies": {},
        }

    # Per-interviewer stats
    interviewer_data = defaultdict(list)
    for entry in data:
        interviewer_data[entry["interviewer"]].append(entry)

    per_interviewer = {}
    all_pass_rates = []
    all_avg_scores = []
    for name, entries in interviewer_data.items():
        decisions = [e["decision"] for e in entries]
        scores = [e["score"] for e in entries]
        hires = sum(1 for d in decisions if d in ("hire", "strong_hire"))
        pass_rate = round(hires / len(decisions) * 100, 1) if decisions else 0
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0
        all_pass_rates.append(pass_rate)
        all_avg_scores.append(avg_score)

        # Score distribution
        score_dist = Counter(scores)
        score_distribution = {str(i): score_dist.get(i, 0) for i in range(1, 6)}

        per_interviewer[name] = {
            "total": len(entries),
            "pass_rate": pass_rate,
            "avg_score": avg_score,
            "scores": scores,
            "score_distribution": score_distribution,
            "decisions": dict(Counter(decisions)),
            "roles": dict(Counter(e["role"] for e in entries)),
        }

    # Per-role stats
    role_data = defaultdict(list)
    for entry in data:
        role_data[entry["role"]].append(entry)

    per_role = {}
    for role, entries in role_data.items():
        decisions = Counter(e["decision"] for e in entries)
        per_role[role] = {
            "total": len(entries),
            "decisions": dict(decisions),
            "avg_score": round(sum(e["score"] for e in entries) / len(entries), 2),
        }

    # Per-interviewer per-role pass rates (for calibration heatmap)
    calibration = {}
    for name in interviewer_data:
        calibration[name] = {}
        for role in role_data:
            role_entries = [e for e in interviewer_data[name] if e["role"] == role]
            if role_entries:
                hires = sum(1 for e in role_entries if e["decision"] in ("hire", "strong_hire"))
                calibration[name][role] = round(hires / len(role_entries) * 100, 1)

    # Agreement matrix
    candidate_interviews = defaultdict(list)
    for entry in data:
        candidate_interviews[entry["candidate"]].append(entry)

    agreement_pairs = defaultdict(lambda: {"agree": 0, "total": 0})
    for candidate, entries in candidate_interviews.items():
        if len(entries) < 2:
            continue
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                a, b = entries[i], entries[j]
                pair_key = tuple(sorted([a["interviewer"], b["interviewer"]]))
                agreement_pairs[pair_key]["total"] += 1
                a_pos = a["decision"] in ("hire", "strong_hire")
                b_pos = b["decision"] in ("hire", "strong_hire")
                if a_pos == b_pos:
                    agreement_pairs[pair_key]["agree"] += 1

    agreement_matrix = {}
    for (a, b), counts in agreement_pairs.items():
        rate = round(counts["agree"] / counts["total"] * 100, 1) if counts["total"] > 0 else None
        agreement_matrix[f"{a} | {b}"] = {
            "rate": rate, "total": counts["total"],
            "interviewer_a": a, "interviewer_b": b,
        }

    # Consistency score (0-100)
    if len(all_pass_rates) > 1:
        pr_mean = sum(all_pass_rates) / len(all_pass_rates)
        pr_variance = sum((x - pr_mean) ** 2 for x in all_pass_rates) / len(all_pass_rates)
        pr_std = math.sqrt(pr_variance)

        sc_mean = sum(all_avg_scores) / len(all_avg_scores)
        sc_variance = sum((x - sc_mean) ** 2 for x in all_avg_scores) / len(all_avg_scores)
        sc_std = math.sqrt(sc_variance)

        agreement_rates = [v["rate"] for v in agreement_matrix.values() if v["rate"] is not None]
        avg_agreement = sum(agreement_rates) / len(agreement_rates) if agreement_rates else 50

        # Lower variance = higher consistency; higher agreement = higher consistency
        variance_score = max(0, 100 - (pr_std * 2 + sc_std * 20))
        consistency_score = round((variance_score * 0.5 + avg_agreement * 0.5), 0)
        consistency_score = max(0, min(100, consistency_score))
    else:
        consistency_score = 100

    # Theme frequencies
    all_themes = []
    for entry in data:
        all_themes.extend(entry.get("themes", []))
    theme_frequencies = dict(Counter(all_themes))

    # Sentiment timeline (monthly averages)
    monthly_sentiment = defaultdict(list)
    for entry in data:
        month = entry.get("date", "")[:7]  # YYYY-MM
        if month:
            monthly_sentiment[month].append(entry.get("sentiment", 0))

    sentiment_timeline = {}
    for month in sorted(monthly_sentiment.keys()):
        vals = monthly_sentiment[month]
        sentiment_timeline[month] = round(sum(vals) / len(vals), 2)

    # Word frequencies (for word cloud)
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
                  "of", "with", "by", "from", "was", "were", "is", "are", "been", "be",
                  "have", "has", "had", "do", "does", "did", "will", "would", "could",
                  "should", "may", "might", "can", "this", "that", "these", "those",
                  "i", "we", "they", "them", "their", "it", "its", "not", "no", "yes",
                  "our", "my", "your", "his", "her", "some", "any", "also", "very",
                  "about", "more", "than", "just", "only", "during", "as", "well",
                  "into", "how", "what", "when", "where", "which", "who", "whom"}
    word_counter = Counter()
    for entry in data:
        words = re.findall(r'\b[a-z]{3,}\b', entry.get("feedback_text", "").lower())
        word_counter.update(w for w in words if w not in stop_words)
    word_frequencies = dict(word_counter.most_common(80))

    # Red flags
    red_flags = []
    if len(all_pass_rates) > 2:
        pr_mean = sum(all_pass_rates) / len(all_pass_rates)
        pr_std = math.sqrt(sum((x - pr_mean) ** 2 for x in all_pass_rates) / len(all_pass_rates))
        for name, stats in per_interviewer.items():
            if abs(stats["pass_rate"] - pr_mean) > pr_std * 1.5:
                direction = "low" if stats["pass_rate"] < pr_mean else "high"
                severity = "high" if abs(stats["pass_rate"] - pr_mean) > pr_std * 2 else "medium"
                if direction == "low":
                    red_flags.append({
                        "type": "outlier_interviewer",
                        "severity": severity,
                        "description": f"{name} has a {stats['pass_rate']}% pass rate — significantly below the team average of {pr_mean:.0f}%.",
                        "interviewer": name,
                    })
                else:
                    red_flags.append({
                        "type": "outlier_interviewer",
                        "severity": severity,
                        "description": f"{name} has a {stats['pass_rate']}% pass rate — significantly above the team average of {pr_mean:.0f}%.",
                        "interviewer": name,
                    })

    for pair_key, pair_data in agreement_matrix.items():
        if pair_data["rate"] is not None and pair_data["rate"] < 30 and pair_data["total"] >= 2:
            red_flags.append({
                "type": "disagreement_pair",
                "severity": "high",
                "description": f"{pair_data['interviewer_a']} and {pair_data['interviewer_b']} agree on only {pair_data['rate']}% of shared candidates ({pair_data['total']} cases).",
            })

    # Executive summary
    total = len(data)
    unique_interviewers = len(interviewer_data)
    unique_candidates = len(candidate_interviews)
    overall_hires = sum(1 for e in data if e["decision"] in ("hire", "strong_hire"))
    overall_pass_rate = round(overall_hires / total * 100, 1) if total else 0

    summary_parts = [
        f"Analyzed {total} interview feedback entries from {unique_interviewers} interviewers across {unique_candidates} candidates.",
        f"Overall pass rate is {overall_pass_rate}% with a consistency score of {consistency_score}/100.",
    ]
    if red_flags:
        summary_parts.append(f"Detected {len(red_flags)} calibration concern{'s' if len(red_flags) != 1 else ''} requiring attention.")
    if per_interviewer:
        toughest = min(per_interviewer.items(), key=lambda x: x[1]["pass_rate"])
        most_lenient = max(per_interviewer.items(), key=lambda x: x[1]["pass_rate"])
        summary_parts.append(
            f"Toughest grader: {toughest[0]} ({toughest[1]['pass_rate']}% pass rate). "
            f"Most lenient: {most_lenient[0]} ({most_lenient[1]['pass_rate']}% pass rate)."
        )

    # Top 3 insights
    top_insights = []
    if per_interviewer:
        toughest = min(per_interviewer.items(), key=lambda x: x[1]["pass_rate"])
        most_lenient = max(per_interviewer.items(), key=lambda x: x[1]["pass_rate"])
        avg_pr = sum(s["pass_rate"] for s in per_interviewer.values()) / len(per_interviewer)
        top_insights.append(
            f"{toughest[0]} has a {toughest[1]['pass_rate']}% pass rate — "
            f"{abs(toughest[1]['pass_rate'] - avg_pr):.0f} points below team average. Consider calibration review."
        )
        top_insights.append(
            f"{most_lenient[0]} passes {most_lenient[1]['pass_rate']}% of candidates — "
            f"{abs(most_lenient[1]['pass_rate'] - avg_pr):.0f} points above average. May need bar-raising."
        )
    if agreement_matrix:
        worst_pair = min(
            ((k, v) for k, v in agreement_matrix.items() if v["rate"] is not None),
            key=lambda x: x[1]["rate"], default=None
        )
        if worst_pair:
            top_insights.append(
                f"{worst_pair[1]['interviewer_a']} and {worst_pair[1]['interviewer_b']} "
                f"have the lowest agreement rate ({worst_pair[1]['rate']}%). "
                f"Pair calibration sessions recommended."
            )

    return {
        "entries": data,
        "per_interviewer": per_interviewer,
        "per_role": per_role,
        "calibration": calibration,
        "agreement_matrix": agreement_matrix,
        "consistency_score": consistency_score,
        "theme_frequencies": theme_frequencies,
        "sentiment_timeline": sentiment_timeline,
        "red_flags": red_flags,
        "executive_summary": " ".join(summary_parts),
        "top_insights": top_insights[:3],
        "word_frequencies": word_frequencies,
        "stats": {
            "total_interviews": total,
            "unique_interviewers": unique_interviewers,
            "unique_candidates": unique_candidates,
            "overall_pass_rate": overall_pass_rate,
            "consistency_score": consistency_score,
        },
    }


# --- Routes ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def get_data():
    role = request.args.get("role")
    interviewer = request.args.get("interviewer")
    decision = request.args.get("decision")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    filtered = feedback_store[:]
    if role:
        filtered = [e for e in filtered if e["role"] == role]
    if interviewer:
        filtered = [e for e in filtered if e["interviewer"] == interviewer]
    if decision:
        filtered = [e for e in filtered if e["decision"] == decision]
    if date_from:
        filtered = [e for e in filtered if e.get("date", "") >= date_from]
    if date_to:
        filtered = [e for e in filtered if e.get("date", "") <= date_to]

    return jsonify(compute_analytics(filtered))


@app.route("/api/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        return jsonify({"error": "No files provided"}), 400

    files = request.files.getlist("files")
    added = 0
    for f in files:
        if not f.filename:
            continue
        content = f.read().decode("utf-8", errors="replace")
        entries = parse_file(f.filename, content)
        assign_ids(entries)
        feedback_store.extend(entries)
        added += len(entries)

    return jsonify({"added": added, "total": len(feedback_store)})


@app.route("/api/paste", methods=["POST"])
def paste():
    body = request.get_json(silent=True) or {}
    text = body.get("text", "")
    if not text.strip():
        return jsonify({"error": "No text provided"}), 400

    entries = parse_file("paste.txt", text)
    assign_ids(entries)
    feedback_store.extend(entries)
    return jsonify({"added": len(entries), "total": len(feedback_store)})


@app.route("/api/reset", methods=["POST"])
def reset():
    global feedback_store
    feedback_store = load_sample_data()
    return jsonify({"status": "reset", "total": len(feedback_store)})


if __name__ == "__main__":
    feedback_store = load_sample_data()
    print(f"Loaded {len(feedback_store)} sample feedback entries")
    print("Starting Interview Insights on http://localhost:8000")
    app.run(host="0.0.0.0", port=8000, debug=True)
