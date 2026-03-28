"""HireSignal — Interview Feedback Intelligence for Engineering Hiring Teams."""

import base64
import csv
import glob
import io
import json
import math
import os
import re
import subprocess
import tempfile
import threading
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from flask import Flask, jsonify, render_template, request, send_from_directory

from mock_greenhouse import (
    get_mock_greenhouse_payload,
    get_mock_greenhouse_sync_payload,
)

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB upload limit

# In-memory feedback store
feedback_store = []
chat_sessions = {}
upload_jobs = {}  # job_id -> {status, progress, message, result}
DECKS_DIR = os.path.join(os.path.dirname(__file__), "data", "decks")
dataset_registry = []
active_dataset_id = "all"

# Greenhouse connection state
greenhouse_state = {"connected": False, "last_sync": None, "api_key": None}
greenhouse_api_key = None
GREENHOUSE_BASE_URL = "https://harvest.greenhouse.io/v1"

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
    """Load sample data from JSON file if it exists, otherwise return empty list."""
    sample_path = os.path.join(os.path.dirname(__file__), "data", "sample.json")
    if not os.path.exists(sample_path):
        return []
    try:
        with open(sample_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def load_latest_session():
    """Load the most recent saved session if one exists."""
    ensure_sessions_dir()
    session_files = sorted(
        glob.glob(os.path.join(SESSIONS_DIR, "session_*.json")),
        reverse=True,
    )
    for filepath in session_files:
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            continue
    return []


def load_initial_data():
    """Resume the latest saved session when available, otherwise use bundled sample data."""
    latest_session = load_latest_session()
    if latest_session:
        return latest_session, "session"

    sample_data = load_sample_data()
    if sample_data:
        return sample_data, "sample"

    return [], "empty"


def run_llm_prompt(prompt, timeout=180):
    """Run the configured LLM backend and return the model's text output."""
    backend = _active_llm_backend()

    if backend == "claude":
        result = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()

    if backend == "codex":
        model = os.environ.get("INTERVIEW_INSIGHTS_CODEX_MODEL", "gpt-5.3-codex").strip()
        reasoning = os.environ.get("INTERVIEW_INSIGHTS_CODEX_REASONING", "medium").strip()
        fd, output_path = tempfile.mkstemp(prefix="hiresignal-codex-", suffix=".txt")
        os.close(fd)
        try:
            subprocess.run(
                [
                    "codex",
                    "exec",
                    "-m",
                    model,
                    "-c",
                    f'reasoning_effort="{reasoning}"',
                    "--skip-git-repo-check",
                    "--sandbox",
                    "read-only",
                    "--output-last-message",
                    output_path,
                    prompt,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True,
            )
            with open(output_path, "r") as f:
                return f.read().strip()
        finally:
            try:
                os.remove(output_path)
            except OSError:
                pass

    if backend == "ollama":
        import urllib.request
        model = llm_config.get("ollama_model", "qwen3.5:0.8b")
        payload = json.dumps({
            "model": model,
            "think": False,
            "stream": False,
            "messages": [
                {"role": "system", "content": "You are a structured data extractor. Return ONLY valid JSON, no explanation, no markdown fences."},
                {"role": "user", "content": prompt},
            ],
        }).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            return result.get("message", {}).get("content", "").strip()

    raise ValueError(f"Unsupported LLM backend: {backend}")


# ── LLM backend config (runtime-switchable) ──────────────────────────────────
llm_config = {
    "backend": os.environ.get("INTERVIEW_INSIGHTS_LLM_BACKEND", "claude").strip().lower(),
    "ollama_model": os.environ.get("INTERVIEW_INSIGHTS_OLLAMA_MODEL", "qwen3.5:0.8b").strip(),
}


def _active_llm_backend():
    return llm_config.get("backend", "claude")


def _check_backend_availability():
    """Check which backends are available on this machine."""
    import shutil
    available = {}

    available["claude"] = shutil.which("claude") is not None

    available["codex"] = shutil.which("codex") is not None

    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        available["ollama"] = True
    except Exception:
        available["ollama"] = False

    return available


def _trim_chat_sessions(max_sessions=100, max_turns=12):
    if len(chat_sessions) > max_sessions:
        ordered = sorted(
            chat_sessions.items(),
            key=lambda item: item[1].get("updated_at", 0),
            reverse=True,
        )
        keep = dict(ordered[:max_sessions])
        chat_sessions.clear()
        chat_sessions.update(keep)

    for session in chat_sessions.values():
        turns = session.get("turns", [])
        if len(turns) > max_turns:
            session["turns"] = turns[-max_turns:]


def get_chat_session(session_id):
    key = (session_id or "").strip()[:120]
    if not key:
        return None
    session = chat_sessions.setdefault(key, {"turns": [], "updated_at": time.time()})
    session["updated_at"] = time.time()
    _trim_chat_sessions()
    return session


def ensure_decks_dir():
    os.makedirs(DECKS_DIR, exist_ok=True)


def _dataset_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _make_dataset_id(prefix="dataset"):
    return f"{prefix}_{int(time.time() * 1000)}"


def create_dataset(name, source="manual", dataset_id=None):
    dataset = {
        "id": dataset_id or _make_dataset_id(source or "dataset"),
        "name": (name or "Untitled Dataset").strip()[:120] or "Untitled Dataset",
        "source": source or "manual",
        "created_at": _dataset_timestamp(),
    }
    existing = next((item for item in dataset_registry if item["id"] == dataset["id"]), None)
    if existing:
        existing.update(dataset)
        return existing
    dataset_registry.append(dataset)
    return dataset


def rebuild_dataset_registry():
    global dataset_registry, active_dataset_id
    registry = []
    seen = {}
    existing_lookup = {item["id"]: item for item in dataset_registry}
    if not feedback_store:
        dataset_registry = []
        active_dataset_id = "all"
        return

    for entry in feedback_store:
        dataset_id = str(entry.get("dataset_id") or "").strip()
        if not dataset_id:
            dataset_id = "legacy"
            entry["dataset_id"] = dataset_id
            entry["dataset_name"] = entry.get("dataset_name") or "Imported Feedback"
            entry["dataset_source"] = entry.get("dataset_source") or entry.get("source") or "manual"
        if dataset_id not in seen:
            existing = existing_lookup.get(dataset_id, {})
            seen[dataset_id] = {
                "id": dataset_id,
                "name": entry.get("dataset_name") or f"Dataset {len(seen) + 1}",
                "source": entry.get("dataset_source") or entry.get("source") or "manual",
                "created_at": entry.get("dataset_created_at") or existing.get("created_at") or _dataset_timestamp(),
            }
            registry.append(seen[dataset_id])

    dataset_registry = registry
    valid_ids = {item["id"] for item in dataset_registry}
    if active_dataset_id != "all" and active_dataset_id not in valid_ids:
        active_dataset_id = dataset_registry[0]["id"] if dataset_registry else "all"


def assign_dataset_metadata(entries, dataset):
    for entry in entries:
        entry["dataset_id"] = dataset["id"]
        entry["dataset_name"] = dataset["name"]
        entry["dataset_source"] = dataset["source"]
        entry["dataset_created_at"] = dataset["created_at"]
    rebuild_dataset_registry()


def set_active_dataset(dataset_id):
    global active_dataset_id
    rebuild_dataset_registry()
    if dataset_id == "all":
        active_dataset_id = "all"
        return True
    if any(item["id"] == dataset_id for item in dataset_registry):
        active_dataset_id = dataset_id
        return True
    return False


def get_active_entries():
    rebuild_dataset_registry()
    if active_dataset_id == "all":
        return feedback_store[:]
    return [entry for entry in feedback_store if entry.get("dataset_id") == active_dataset_id]


def build_dataset_summary():
    rebuild_dataset_registry()
    counts = Counter(entry.get("dataset_id") for entry in feedback_store if entry.get("dataset_id"))
    summary = []
    for dataset in dataset_registry:
        dataset_rows = [entry for entry in feedback_store if entry.get("dataset_id") == dataset["id"]]
        roles = sorted({(entry.get("role") or "Unknown").strip() for entry in dataset_rows if (entry.get("role") or "").strip()})
        interviewers = sorted({(entry.get("interviewer") or "Unknown").strip() for entry in dataset_rows if (entry.get("interviewer") or "").strip()})
        dates = sorted(str(entry.get("date") or "")[:10] for entry in dataset_rows if entry.get("date"))
        job_ids = sorted({str(entry.get("source_job_id")) for entry in dataset_rows if entry.get("source_job_id")})
        offices = sorted({entry.get("source_office") for entry in dataset_rows if entry.get("source_office")})
        departments = sorted({entry.get("source_department") for entry in dataset_rows if entry.get("source_department")})
        summary.append({
            **dataset,
            "entries": counts.get(dataset["id"], 0),
            "active": dataset["id"] == active_dataset_id,
            "roles": roles,
            "role_count": len(roles),
            "interviewer_count": len(interviewers),
            "job_count": len(job_ids) or len(roles),
            "office_count": len(offices),
            "department_count": len(departments),
            "date_start": dates[0] if dates else None,
            "date_end": dates[-1] if dates else None,
        })
    return {
        "active_dataset_id": active_dataset_id,
        "datasets": summary,
        "all_entries": len(feedback_store),
        "all_candidates": len({entry.get("candidate") for entry in feedback_store if entry.get("candidate")}),
    }


def dataset_entries(dataset_id):
    if dataset_id == "all":
        return feedback_store[:]
    return [entry for entry in feedback_store if entry.get("dataset_id") == dataset_id]


def _dataset_group_key(entry, split_mode):
    if split_mode == "job":
        job_id = entry.get("source_job_id")
        job_name = (entry.get("source_job_name") or entry.get("role") or "Unknown").strip() or "Unknown"
        return f"{job_name} [{job_id}]" if job_id else job_name
    if split_mode == "role":
        return (entry.get("role") or "Unknown").strip() or "Unknown"
    return None


def ingest_grouped_entries(entries, dataset_mode="new", dataset_name="", source="manual", split_mode="none"):
    global feedback_store
    if dataset_mode == "replace":
        feedback_store = []
        rebuild_dataset_registry()

    if dataset_mode == "merge" and active_dataset_id != "all":
        target_dataset = next((item for item in dataset_registry if item["id"] == active_dataset_id), None)
        if target_dataset is None:
            target_dataset = create_dataset(dataset_name or f"{source.title()} {_dataset_timestamp()}", source)
        assign_dataset_metadata(entries, target_dataset)
        assign_ids(entries)
        feedback_store.extend(entries)
        set_active_dataset(target_dataset["id"])
        auto_save()
        return {"datasets_created": [target_dataset], "entries_added": len(entries)}

    groups = defaultdict(list)
    if split_mode in {"job", "role"}:
        for entry in entries:
            groups[_dataset_group_key(entry, split_mode)].append(entry)
    else:
        groups[dataset_name or f"{source.title()} {_dataset_timestamp()}"] = entries

    created = []
    total_added = 0
    first_dataset_id = None
    base_name = dataset_name.strip() if dataset_name else ""
    for group_name, group_entries in groups.items():
        if split_mode in {"job", "role"}:
            display_name = f"{base_name} · {group_name}" if base_name else f"{source.title()} · {group_name}"
        else:
            display_name = group_name
        dataset = create_dataset(display_name, source)
        assign_dataset_metadata(group_entries, dataset)
        assign_ids(group_entries)
        feedback_store.extend(group_entries)
        created.append(dataset)
        total_added += len(group_entries)
        if first_dataset_id is None:
            first_dataset_id = dataset["id"]

    if first_dataset_id:
        set_active_dataset(first_dataset_id)
    auto_save()
    return {"datasets_created": created, "entries_added": total_added}


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


def _greenhouse_headers(api_key):
    token = (api_key or "").strip()
    basic = base64.b64encode(f"{token}:".encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/json",
        "User-Agent": "InterviewInsights/1.0",
    }


def _greenhouse_get_json(path, api_key, params=None):
    query = urllib_parse.urlencode(params or {})
    url = f"{GREENHOUSE_BASE_URL}{path}"
    if query:
        url = f"{url}?{query}"
    req = urllib_request.Request(url, headers=_greenhouse_headers(api_key), method="GET")
    with urllib_request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body), dict(resp.headers)


def _greenhouse_collect_pages(path, api_key, params=None):
    page = 1
    items = []
    while True:
        page_params = {"per_page": 100, "page": page}
        if params:
            page_params.update(params)
        payload, _ = _greenhouse_get_json(path, api_key, page_params)
        if not isinstance(payload, list) or not payload:
            break
        items.extend(payload)
        if len(payload) < page_params["per_page"]:
            break
        page += 1
    return items


def _greenhouse_candidate_name(candidate):
    full_name = (candidate or {}).get("name")
    if full_name:
        return full_name
    first_name = (candidate or {}).get("first_name", "").strip()
    last_name = (candidate or {}).get("last_name", "").strip()
    return f"{first_name} {last_name}".strip() or "Unknown"


def _greenhouse_application_context(candidate, application_id):
    applications = (candidate or {}).get("applications") or []
    target = None
    for application in applications:
        if application.get("id") == application_id:
            target = application
            break
    target = target or (applications[0] if applications else {})
    jobs = target.get("jobs") or []
    job_id = None
    job_name = None
    office_name = None
    department_name = None
    if jobs:
        job = jobs[0] or {}
        if isinstance(job, dict):
            job_id = job.get("id")
            job_name = job.get("name") or job.get("title")
            office = job.get("office") or {}
            department = job.get("department") or {}
            if isinstance(office, dict):
                office_name = office.get("name")
            elif isinstance(office, str):
                office_name = office
            if isinstance(department, dict):
                department_name = department.get("name")
            elif isinstance(department, str):
                department_name = department
        if isinstance(job, str):
            job_name = job
    current_stage = target.get("current_stage") or {}
    opening = target.get("opening") or {}
    if not office_name:
        office = target.get("office") or opening.get("office") or {}
        if isinstance(office, dict):
            office_name = office.get("name")
        elif isinstance(office, str):
            office_name = office
    if not department_name:
        department = target.get("department") or opening.get("department") or {}
        if isinstance(department, dict):
            department_name = department.get("name")
        elif isinstance(department, str):
            department_name = department
    return {
        "job_id": job_id or target.get("job_id") or opening.get("job_id"),
        "job_name": job_name or target.get("job_name") or current_stage.get("name") or "Unknown",
        "office": office_name,
        "department": department_name,
    }


def _greenhouse_round_type(scorecard):
    step = (scorecard.get("interview_step") or {}).get("name", "")
    interview = (scorecard.get("interview") or {}).get("name", "")
    label = f"{step} {interview}".lower()
    if "take" in label and "home" in label:
        return "take_home_review"
    if "quiz" in label or "assessment" in label:
        return "technical_quiz"
    if "system" in label and "design" in label:
        return "system_design"
    if "culture" in label or "behavior" in label:
        return "culture_fit"
    if "technical" in label or "coding" in label or "live" in label:
        return "technical_interview"
    return "general"


def _greenhouse_decision(scorecard):
    recommendation = (scorecard.get("overall_recommendation") or "").lower()
    mapping = {
        "strong_yes": "strong_hire",
        "yes": "hire",
        "no_decision": "maybe",
        "no": "no_hire",
        "definitely_not": "strong_no_hire",
    }
    if recommendation in mapping:
        return mapping[recommendation]

    joined = " ".join(
        str(part)
        for part in [
            scorecard.get("overall_recommendation"),
            " ".join(attr.get("note", "") for attr in scorecard.get("attributes") or []),
            " ".join(q.get("answer", "") for q in scorecard.get("questions") or []),
        ]
        if part
    )
    return extract_decision(joined)


def _greenhouse_score(scorecard):
    recommendation = (scorecard.get("overall_recommendation") or "").lower()
    recommendation_score = {
        "strong_yes": 5,
        "yes": 4,
        "no_decision": 3,
        "no": 2,
        "definitely_not": 1,
    }
    ratings = []
    for attr in scorecard.get("attributes") or []:
        rating = str(attr.get("rating", "")).lower()
        if rating in recommendation_score:
            ratings.append(recommendation_score[rating])
        else:
            value = attr.get("score") or attr.get("value")
            try:
                ratings.append(max(1, min(5, int(float(value)))))
            except (TypeError, ValueError):
                continue
    if ratings:
        return round(sum(ratings) / len(ratings))
    return recommendation_score.get(recommendation, 3)


def _greenhouse_feedback_text(scorecard):
    parts = []
    recommendation = scorecard.get("overall_recommendation")
    if recommendation:
        parts.append(f"Overall recommendation: {recommendation}.")

    for attr in scorecard.get("attributes") or []:
        name = attr.get("name") or "Attribute"
        rating = attr.get("rating")
        note = attr.get("note") or ""
        fragment = f"{name}: {rating}" if rating else name
        if note:
            fragment += f". {note}"
        parts.append(fragment.strip())

    for question in scorecard.get("questions") or []:
        answer = (question or {}).get("answer")
        prompt = (question or {}).get("question")
        if answer:
            parts.append(f"{prompt}: {answer}" if prompt else str(answer))

    text = "\n".join(part.strip() for part in parts if part and str(part).strip())
    return text[:2000]


def map_greenhouse_scorecard(scorecard, candidate_lookup):
    candidate = candidate_lookup.get(scorecard.get("candidate_id"), {})
    feedback_text = _greenhouse_feedback_text(scorecard)
    interviewer = (scorecard.get("interviewer") or {}).get("name") or (scorecard.get("submitted_by") or {}).get("name") or "Unknown"
    candidate_name = _greenhouse_candidate_name(candidate)
    application_context = _greenhouse_application_context(candidate, scorecard.get("application_id"))
    role = application_context["job_name"]
    decision = _greenhouse_decision(scorecard)
    score = _greenhouse_score(scorecard)
    date_value = scorecard.get("interviewed_at") or scorecard.get("submitted_at") or datetime.now().strftime("%Y-%m-%d")
    date = str(date_value)[:10]

    return {
        "id": None,
        "source": "greenhouse",
        "source_id": scorecard.get("id"),
        "source_candidate_id": scorecard.get("candidate_id"),
        "source_application_id": scorecard.get("application_id"),
        "source_job_id": application_context.get("job_id"),
        "source_job_name": application_context.get("job_name"),
        "source_department": application_context.get("department"),
        "source_office": application_context.get("office"),
        "interviewer": interviewer,
        "candidate": candidate_name,
        "role": role,
        "decision": decision,
        "score": score,
        "themes": extract_themes(feedback_text),
        "sentiment": compute_sentiment(feedback_text),
        "date": date,
        "feedback_text": feedback_text,
        "round_type": _greenhouse_round_type(scorecard),
    }


def normalize_greenhouse_payload(scorecards, candidates):
    candidate_lookup = {candidate.get("id"): candidate for candidate in candidates}
    entries = []
    for scorecard in scorecards:
        try:
            entries.append(map_greenhouse_scorecard(scorecard, candidate_lookup))
        except Exception as exc:
            print(f"Skipping malformed Greenhouse scorecard {scorecard.get('id')}: {exc}")
    return entries


def fetch_greenhouse_harvest_data(api_key):
    scorecards = _greenhouse_collect_pages("/scorecards", api_key)
    candidate_ids = sorted({scorecard.get("candidate_id") for scorecard in scorecards if scorecard.get("candidate_id")})
    candidates = []
    for candidate_id in candidate_ids:
        try:
            candidate, _ = _greenhouse_get_json(f"/candidates/{candidate_id}", api_key)
            candidates.append(candidate)
        except urllib_error.HTTPError as exc:
            if exc.code == 404:
                continue
            raise
    return {"scorecards": scorecards, "candidates": candidates}


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


def clean_pdf_text(text):
    """Clean up PDF-extracted text that has broken spacing."""
    # Fix single-word-per-line patterns (common in some PDF exports)
    # Collapse lines where each line is a single word
    lines = text.split('\n')
    cleaned = []
    buffer = []
    for line in lines:
        stripped = line.strip()
        # If line is a single short word (likely broken spacing), buffer it
        if stripped and len(stripped.split()) == 1 and len(stripped) < 30 and not stripped.startswith(('-', '•', '✅', '🔴', '🟢', '🟡', '#')):
            buffer.append(stripped)
        else:
            if buffer:
                cleaned.append(' '.join(buffer))
                buffer = []
            cleaned.append(line)
    if buffer:
        cleaned.append(' '.join(buffer))
    result = '\n'.join(cleaned)
    # Collapse excessive whitespace
    result = re.sub(r' {3,}', ' ', result)
    result = re.sub(r'\n{4,}', '\n\n\n', result)
    return result


def extract_pdf_text(file_bytes):
    """Extract raw text from a PDF file."""
    if PdfReader is None:
        raise ValueError("PDF support requires PyPDF2. Install it with: pip install PyPDF2")
    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(clean_pdf_text(text))
    full_text = "\n\n---PAGE BREAK---\n\n".join(pages_text)
    if not full_text.strip():
        raise ValueError("Could not extract any text from the PDF. The file may be image-based or empty.")
    return full_text


def _validate_llm_entries(raw_entries):
    """Validate and normalize entries from LLM response."""
    valid = []
    for e in raw_entries:
        try:
            valid.append({
                "id": None,
                "interviewer": e.get("interviewer", "Unknown"),
                "candidate": e.get("candidate", "Unknown"),
                "role": e.get("role", "PHP Developer"),
                "decision": e.get("decision", "maybe"),
                "score": max(1, min(5, int(e.get("score", 3)))),
                "themes": e.get("themes", ["technical_skills"]),
                "sentiment": float(e.get("sentiment", 0.0)),
                "date": e.get("date", datetime.now().strftime("%Y-%m-%d")),
                "feedback_text": e.get("feedback_text", "")[:2000],
                "round_type": e.get("round_type", "general"),
            })
        except (ValueError, TypeError):
            continue
    return valid


def parse_with_llm(text):
    """Use the configured LLM CLI to parse unstructured feedback text into structured entries."""
    prompt = """You are a structured data extractor for interview feedback documents.
The text below contains one or more interview feedback entries. These may be:
- Technical interview feedback
- Take-home coding task reviews
- Quiz/assessment evaluations
- Culture fit interviews

Each time a NEW CANDIDATE is discussed, that is a SEPARATE entry. Look for candidate names, reviewer names, and any section breaks.

Extract each individual feedback into a JSON array. Each entry must have:
- "interviewer": string (the reviewer/evaluator name)
- "candidate": string (the candidate/applicant name)
- "role": string (default "PHP Developer" if not specified)
- "decision": string (one of: "strong_hire", "hire", "maybe", "no_hire", "strong_no_hire"). Map "Proceed" or checkmarks to "hire", "Do not proceed" or X marks to "no_hire"
- "score": integer 1-5 (infer from tone if not explicit)
- "themes": array from: ["technical_skills", "communication", "culture_fit", "problem_solving", "leadership", "system_design", "coding_ability"]
- "sentiment": float between -1.0 and 1.0
- "date": string "YYYY-MM-DD" (use today if not found)
- "feedback_text": string (the key feedback content for this entry, keep the important details)
- "round_type": string (one of: "take_home_review", "technical_quiz", "technical_interview", "culture_fit", "general")

CRITICAL: Each candidate-reviewer combination is a SEPARATE entry. Do NOT merge multiple candidates into one entry.
Return ONLY the JSON array.

Text to parse:

""" + text

    try:
        output = run_llm_prompt(prompt, timeout=180)
        json_match = re.search(r'\[.*\]', output, re.DOTALL)
        if json_match:
            entries = json.loads(json_match.group())
            if isinstance(entries, list) and entries:
                return _validate_llm_entries(entries)
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, Exception) as exc:
        print(f"LLM parsing failed ({exc}), falling back to heuristic parser")

    # Fallback to heuristic parsing
    blocks = re.split(r'\n{2,}---\n{2,}|\n{3,}|\f', text)
    entries = []
    for block in blocks:
        block = block.strip()
        if len(block) > 20:
            entries.append(parse_text_feedback(block))
    return entries if entries else [parse_text_feedback(text)]


def parse_pdf_feedback(file_bytes):
    """Extract text from PDF and use LLM to parse into structured feedback entries."""
    full_text = extract_pdf_text(file_bytes)

    # For long PDFs, process in chunks to avoid context limits
    # Split by page breaks and group into chunks of ~5 pages
    pages = full_text.split("---PAGE BREAK---")
    if len(pages) <= 3:
        return parse_with_llm(full_text)

    # Process in chunks
    all_entries = []
    chunk_size = 4  # pages per chunk
    for i in range(0, len(pages), chunk_size):
        chunk = "\n\n".join(pages[i:i + chunk_size])
        if chunk.strip():
            print(f"  Processing PDF pages {i+1}-{min(i+chunk_size, len(pages))} of {len(pages)}...")
            entries = parse_with_llm(chunk)
            all_entries.extend(entries)

    return all_entries if all_entries else parse_with_llm(full_text)


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


def _merge_analysis_into_entry(entry, analysis):
    """Apply deep-analysis output (or heuristic fallback) onto a feedback entry."""
    payload = analysis if analysis is not None else _heuristic_analysis(entry)
    entry["reasons_positive"] = payload.get("reasons_positive", []) if isinstance(payload.get("reasons_positive"), list) else []
    entry["reasons_negative"] = payload.get("reasons_negative", []) if isinstance(payload.get("reasons_negative"), list) else []
    round_type = payload.get("round_type", "general")
    entry["round_type"] = round_type if round_type in VALID_ROUND_TYPES else "general"
    raw_tags = payload.get("style_tags", []) if isinstance(payload.get("style_tags"), list) else []
    entry["style_tags"] = [t for t in raw_tags if t in VALID_STYLE_TAGS] or ["balanced"]
    entry["key_quote"] = str(payload.get("key_quote", ""))[:300]


def _apply_analysis_results(entries, results):
    """Write analysis results back onto a list of feedback entries."""
    for idx, entry in enumerate(entries):
        analysis = results[idx] if idx < len(results) and results[idx] is not None else None
        _merge_analysis_into_entry(entry, analysis)


def _needs_deep_analysis(entries):
    """Check whether entries are missing enrichment required for advanced analytics."""
    required_fields = ("reasons_positive", "reasons_negative", "round_type", "style_tags", "key_quote")
    return any(any(field not in entry for field in required_fields) for entry in entries)


def ensure_deep_analysis(entries, persist=False):
    """Ensure the provided entries are enriched with deep-analysis fields."""
    if not entries or not _needs_deep_analysis(entries):
        return False

    results = _run_deep_analysis(entries)
    _apply_analysis_results(entries, results)
    if persist:
        auto_save()
    return True


def compute_analytics(data):
    """Compute all analytics from feedback data."""
    if not data:
        return {
            "entries": [], "per_interviewer": {}, "per_role": {},
            "agreement_matrix": {}, "consistency_score": 0,
            "theme_frequencies": {}, "sentiment_timeline": {},
            "red_flags": [], "executive_summary": "No data available.",
            "top_insights": [], "word_frequencies": {},
            "candidate_outcomes": [], "interviewer_leaderboard": [],
            "round_distribution": {}, "has_deep_analysis": False,
            "decision_funnel": [],
            "candidate_review_queue": [],
            "interviewer_risk": [],
            "role_health": [],
            "reason_signals": {"positive": [], "negative": [], "blockers": []},
            "round_insights": [],
            "stats": {
                "total_interviews": 0, "unique_interviewers": 0,
                "unique_candidates": 0, "overall_pass_rate": 0,
                "consistency_score": 0,
                "conflicted_candidates": 0,
                "high_risk_interviewers": 0,
                "analysis_coverage": 0,
            },
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

        # Theme frequencies for this interviewer
        interviewer_themes = []
        for e in entries:
            interviewer_themes.extend(e.get("themes", []))
        theme_freq = dict(Counter(interviewer_themes))

        per_interviewer[name] = {
            "total": len(entries),
            "pass_rate": pass_rate,
            "avg_score": avg_score,
            "scores": scores,
            "score_distribution": score_distribution,
            "decisions": dict(Counter(decisions)),
            "roles": dict(Counter(e["role"] for e in entries)),
            "themes": theme_freq,
        }

    # Per-role stats
    role_data = defaultdict(list)
    for entry in data:
        role_data[entry["role"]].append(entry)

    per_role = {}
    for role, entries in role_data.items():
        decisions = Counter(e["decision"] for e in entries)
        hires = sum(1 for e in entries if e["decision"] in ("hire", "strong_hire"))
        pass_rate = round(hires / len(entries) * 100, 1) if entries else 0
        # Per-interviewer stats for this role
        role_interviewers = defaultdict(list)
        for e in entries:
            role_interviewers[e["interviewer"]].append(e)
        interviewer_stats = {}
        for iname, ientries in role_interviewers.items():
            ihires = sum(1 for e in ientries if e["decision"] in ("hire", "strong_hire"))
            interviewer_stats[iname] = {
                "total": len(ientries),
                "pass_rate": round(ihires / len(ientries) * 100, 1) if ientries else 0,
                "avg_score": round(sum(e["score"] for e in ientries) / len(ientries), 2),
            }
        per_role[role] = {
            "total": len(entries),
            "decisions": dict(decisions),
            "avg_score": round(sum(e["score"] for e in entries) / len(entries), 2),
            "pass_rate": pass_rate,
            "interviewers": interviewer_stats,
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

    # Candidate outcomes
    candidate_groups = defaultdict(list)
    for entry in data:
        candidate_groups[entry["candidate"]].append(entry)

    candidate_outcomes = []
    for cand, entries_list in candidate_groups.items():
        interviews = []
        for e in entries_list:
            interviews.append({
                "interviewer": e["interviewer"],
                "decision": e["decision"],
                "score": e["score"],
                "sentiment": e.get("sentiment", 0.0),
            })
        decisions_list = [e["decision"] for e in entries_list]
        scores_list = [e["score"] for e in entries_list]
        # Majority decision
        decision_counts = Counter(decisions_list)
        consensus = decision_counts.most_common(1)[0][0]
        avg_sc = round(sum(scores_list) / len(scores_list), 2) if scores_list else 0
        candidate_outcomes.append({
            "candidate": cand,
            "role": entries_list[0]["role"],
            "interviews": interviews,
            "consensus": consensus,
            "avg_score": avg_sc,
        })
    candidate_outcomes.sort(key=lambda x: x["avg_score"], reverse=True)

    # Interviewer leaderboard
    sorted_interviewers = sorted(per_interviewer.items(), key=lambda x: x[1]["pass_rate"], reverse=True)
    interviewer_leaderboard = []
    for idx, (name, stats) in enumerate(sorted_interviewers):
        label = ""
        if idx == 0 and len(sorted_interviewers) > 1:
            label = "Most Lenient"
        elif idx == len(sorted_interviewers) - 1 and len(sorted_interviewers) > 1:
            label = "Toughest"
        interviewer_leaderboard.append({
            "name": name,
            "total": stats["total"],
            "pass_rate": stats["pass_rate"],
            "avg_score": stats["avg_score"],
            "label": label,
        })

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

    # Round distribution (from deep analysis enrichment)
    round_counts = Counter()
    has_deep_analysis = False
    for entry in data:
        rt = entry.get("round_type")
        if rt:
            has_deep_analysis = True
            round_counts[rt] += 1
    round_distribution = dict(round_counts) if round_counts else {}

    # Decision funnel
    decision_order = ["strong_hire", "hire", "maybe", "no_hire", "strong_no_hire"]
    decision_labels = {
        "strong_hire": "Strong Hire",
        "hire": "Hire",
        "maybe": "Maybe",
        "no_hire": "No Hire",
        "strong_no_hire": "Strong No Hire",
    }
    decision_counter = Counter(entry["decision"] for entry in data)
    decision_funnel = [
        {
            "decision": key,
            "label": decision_labels[key],
            "count": decision_counter.get(key, 0),
            "pct": round((decision_counter.get(key, 0) / total) * 100, 1) if total else 0,
        }
        for key in decision_order
    ]

    # Candidate review queue
    candidate_review_queue = []
    for cand, entries_list in candidate_groups.items():
        if cand == "Unknown":
            continue
        decisions_list = [e["decision"] for e in entries_list]
        scores_list = [e["score"] for e in entries_list]
        decision_counts = Counter(decisions_list)
        consensus, consensus_votes = decision_counts.most_common(1)[0]
        score_spread = max(scores_list) - min(scores_list) if scores_list else 0
        mixed_decisions = len(decision_counts) > 1
        blocker_counts = Counter(reason for e in entries_list for reason in e.get("reasons_negative", []))
        support_counts = Counter(reason for e in entries_list for reason in e.get("reasons_positive", []))
        rounds = sorted({e.get("round_type", "general") for e in entries_list})
        reviewers = sorted({e["interviewer"] for e in entries_list})
        confidence = round((consensus_votes / len(entries_list)) * 100 - score_spread * 10) if entries_list else 0
        confidence = max(0, min(100, confidence))

        if mixed_decisions or score_spread >= 2 or "maybe" in decision_counts:
            severity = "review"
        elif consensus in ("no_hire", "strong_no_hire"):
            severity = "blocked"
        elif consensus in ("hire", "strong_hire") and confidence >= 75:
            severity = "aligned"
        else:
            severity = "watch"

        candidate_review_queue.append({
            "candidate": cand,
            "role": entries_list[0]["role"],
            "consensus": consensus,
            "confidence": confidence,
            "interview_count": len(entries_list),
            "score_spread": score_spread,
            "mixed_decisions": mixed_decisions,
            "reviewers": reviewers,
            "rounds": rounds,
            "top_blockers": [reason for reason, _ in blocker_counts.most_common(3)],
            "top_supports": [reason for reason, _ in support_counts.most_common(3)],
            "severity": severity,
        })
    candidate_review_queue.sort(
        key=lambda item: (
            {"review": 0, "blocked": 1, "watch": 2, "aligned": 3}.get(item["severity"], 4),
            item["confidence"],
        )
    )

    # Reason signals
    positive_reason_data = defaultdict(lambda: {"count": 0, "candidates": set(), "decisions": [], "scores": []})
    negative_reason_data = defaultdict(lambda: {"count": 0, "candidates": set(), "decisions": [], "scores": []})
    for entry in data:
        candidate_name = entry.get("candidate", "Unknown")
        for reason in entry.get("reasons_positive", []):
            positive_reason_data[reason]["count"] += 1
            positive_reason_data[reason]["candidates"].add(candidate_name)
            positive_reason_data[reason]["decisions"].append(entry["decision"])
            positive_reason_data[reason]["scores"].append(entry["score"])
        for reason in entry.get("reasons_negative", []):
            negative_reason_data[reason]["count"] += 1
            negative_reason_data[reason]["candidates"].add(candidate_name)
            negative_reason_data[reason]["decisions"].append(entry["decision"])
            negative_reason_data[reason]["scores"].append(entry["score"])

    positive_signals = []
    for reason, details in positive_reason_data.items():
        decisions = details["decisions"]
        hires = sum(1 for decision in decisions if decision in ("hire", "strong_hire"))
        positive_signals.append({
            "reason": reason,
            "count": details["count"],
            "candidate_count": len(details["candidates"]),
            "hire_rate": round((hires / len(decisions)) * 100, 1) if decisions else 0,
            "avg_score": round(sum(details["scores"]) / len(details["scores"]), 2) if details["scores"] else 0,
        })
    positive_signals.sort(key=lambda item: (-item["count"], -item["hire_rate"], item["reason"]))

    negative_signals = []
    blocker_signals = []
    for reason, details in negative_reason_data.items():
        decisions = details["decisions"]
        no_hires = sum(1 for decision in decisions if decision in ("no_hire", "strong_no_hire"))
        maybe_count = sum(1 for decision in decisions if decision == "maybe")
        payload = {
            "reason": reason,
            "count": details["count"],
            "candidate_count": len(details["candidates"]),
            "no_hire_rate": round((no_hires / len(decisions)) * 100, 1) if decisions else 0,
            "maybe_rate": round((maybe_count / len(decisions)) * 100, 1) if decisions else 0,
            "avg_score": round(sum(details["scores"]) / len(details["scores"]), 2) if details["scores"] else 0,
        }
        negative_signals.append(payload)
        if payload["count"] >= 2:
            blocker_signals.append(payload)
    negative_signals.sort(key=lambda item: (-item["count"], -item["no_hire_rate"], item["reason"]))
    blocker_signals.sort(key=lambda item: (-item["no_hire_rate"], -item["count"], item["reason"]))

    # Interviewer risk
    team_avg_score = round(sum(e["score"] for e in data) / len(data), 2) if data else 0
    pair_data_by_interviewer = defaultdict(list)
    for pair in agreement_matrix.values():
        pair_data_by_interviewer[pair["interviewer_a"]].append(pair)
        pair_data_by_interviewer[pair["interviewer_b"]].append(pair)

    interviewer_risk = []
    for name, stats in per_interviewer.items():
        entries = interviewer_data[name]
        positive_counts = Counter(reason for e in entries for reason in e.get("reasons_positive", []))
        negative_counts = Counter(reason for e in entries for reason in e.get("reasons_negative", []))
        pair_rates = [pair["rate"] for pair in pair_data_by_interviewer[name] if pair["rate"] is not None]
        disagreement_rate = round(100 - (sum(pair_rates) / len(pair_rates)), 1) if pair_rates else None
        flagged_candidates = sum(1 for candidate in candidate_review_queue if name in candidate["reviewers"] and candidate["severity"] in {"review", "blocked"})
        pass_rate_delta = round(stats["pass_rate"] - overall_pass_rate, 1)
        avg_score_delta = round(stats["avg_score"] - team_avg_score, 2)
        risk_score = abs(pass_rate_delta) * 0.9 + abs(avg_score_delta) * 12 + (disagreement_rate or 20) * 0.45 + flagged_candidates * 4
        risk_score = round(max(0, min(100, risk_score)), 1)
        if pass_rate_delta <= -15:
            stance = "strict"
        elif pass_rate_delta >= 15:
            stance = "lenient"
        else:
            stance = "balanced"

        interviewer_risk.append({
            "name": name,
            "risk_score": risk_score,
            "stance": stance,
            "total": stats["total"],
            "pass_rate": stats["pass_rate"],
            "pass_rate_delta": pass_rate_delta,
            "avg_score": stats["avg_score"],
            "avg_score_delta": avg_score_delta,
            "disagreement_rate": disagreement_rate,
            "flagged_candidates": flagged_candidates,
            "top_positive_reason": positive_counts.most_common(1)[0][0] if positive_counts else "",
            "top_negative_reason": negative_counts.most_common(1)[0][0] if negative_counts else "",
            "style_tags": list({tag for e in entries for tag in e.get("style_tags", [])})[:3],
        })
    interviewer_risk.sort(key=lambda item: (-item["risk_score"], -item["flagged_candidates"], item["name"]))

    # Role health
    role_health = []
    for role, entries in role_data.items():
        role_candidates = [candidate for candidate in candidate_review_queue if candidate["role"] == role]
        blocker_counts = Counter(reason for e in entries for reason in e.get("reasons_negative", []))
        support_counts = Counter(reason for e in entries for reason in e.get("reasons_positive", []))
        interviewer_pass_rates = [details["pass_rate"] for details in per_role[role]["interviewers"].values()]
        calibration_spread = round(max(interviewer_pass_rates) - min(interviewer_pass_rates), 1) if len(interviewer_pass_rates) > 1 else 0
        role_health.append({
            "role": role,
            "total": len(entries),
            "pass_rate": per_role[role]["pass_rate"],
            "avg_score": per_role[role]["avg_score"],
            "decision_mix": per_role[role]["decisions"],
            "calibration_spread": calibration_spread,
            "review_count": sum(1 for candidate in role_candidates if candidate["severity"] in {"review", "blocked"}),
            "top_blockers": [reason for reason, _ in blocker_counts.most_common(3)],
            "top_supports": [reason for reason, _ in support_counts.most_common(3)],
        })
    role_health.sort(key=lambda item: (-item["review_count"], -item["calibration_spread"], item["role"]))

    # Round insights
    round_insights = []
    if has_deep_analysis:
        for round_type in sorted(round_counts):
            round_entries = [entry for entry in data if entry.get("round_type") == round_type]
            round_hires = sum(1 for entry in round_entries if entry["decision"] in ("hire", "strong_hire"))
            negative_counts = Counter(reason for entry in round_entries for reason in entry.get("reasons_negative", []))
            positive_counts = Counter(reason for entry in round_entries for reason in entry.get("reasons_positive", []))
            round_insights.append({
                "round_type": round_type,
                "count": len(round_entries),
                "pass_rate": round((round_hires / len(round_entries)) * 100, 1) if round_entries else 0,
                "avg_score": round(sum(entry["score"] for entry in round_entries) / len(round_entries), 2) if round_entries else 0,
                "top_blocker": negative_counts.most_common(1)[0][0] if negative_counts else "",
                "top_signal": positive_counts.most_common(1)[0][0] if positive_counts else "",
            })

    # Cross-round candidate correlation
    cross_round_correlation = []
    for cand, entries_list in candidate_groups.items():
        if cand == "Unknown":
            continue
        round_scores = {}
        for e in entries_list:
            rt = e.get("round_type") or "unknown"
            if rt not in round_scores:
                round_scores[rt] = {
                    "score": e["score"],
                    "decision": e["decision"],
                    "interviewer": e["interviewer"],
                }
            else:
                # If multiple entries of same round type, average the score
                existing = round_scores[rt]
                existing["score"] = round((existing["score"] + e["score"]) / 2, 1)
        if len(round_scores) >= 2:
            # Candidate has data in multiple round types — interesting for correlation
            cross_round_correlation.append({
                "candidate": cand,
                "role": entries_list[0]["role"],
                "rounds": round_scores,
                "round_types": sorted(round_scores.keys()),
                "avg_score": round(sum(rs["score"] for rs in round_scores.values()) / len(round_scores), 2),
                "consensus": Counter(e["decision"] for e in entries_list).most_common(1)[0][0],
                "agreement": len(set(
                    "positive" if e["decision"] in ("hire", "strong_hire") else "negative"
                    for e in entries_list
                )) == 1,
            })
    cross_round_correlation.sort(key=lambda x: x["candidate"])

    # Round-pair correlation summary (e.g. take_home vs tech_interview)
    round_pair_summary = {}
    all_round_types = sorted({rt for item in cross_round_correlation for rt in item["round_types"]})
    for i, rt_a in enumerate(all_round_types):
        for rt_b in all_round_types[i + 1:]:
            pairs = []
            for item in cross_round_correlation:
                if rt_a in item["rounds"] and rt_b in item["rounds"]:
                    pairs.append({
                        "candidate": item["candidate"],
                        "score_a": item["rounds"][rt_a]["score"],
                        "score_b": item["rounds"][rt_b]["score"],
                        "decision_a": item["rounds"][rt_a]["decision"],
                        "decision_b": item["rounds"][rt_b]["decision"],
                    })
            if pairs:
                scores_a = [p["score_a"] for p in pairs]
                scores_b = [p["score_b"] for p in pairs]
                avg_a = round(sum(scores_a) / len(scores_a), 2)
                avg_b = round(sum(scores_b) / len(scores_b), 2)
                # Simple correlation: how often do both rounds agree on direction
                agreements = sum(
                    1 for p in pairs
                    if (p["decision_a"] in ("hire", "strong_hire")) == (p["decision_b"] in ("hire", "strong_hire"))
                )
                agreement_rate = round((agreements / len(pairs)) * 100, 1) if pairs else 0
                # Score difference
                avg_diff = round(sum(abs(p["score_a"] - p["score_b"]) for p in pairs) / len(pairs), 2)
                round_pair_summary[f"{rt_a} vs {rt_b}"] = {
                    "round_a": rt_a,
                    "round_b": rt_b,
                    "candidates": len(pairs),
                    "avg_score_a": avg_a,
                    "avg_score_b": avg_b,
                    "agreement_rate": agreement_rate,
                    "avg_score_diff": avg_diff,
                    "pairs": pairs,
                }

    conflicted_candidates = sum(1 for candidate in candidate_review_queue if candidate["severity"] in {"review", "blocked"})
    high_risk_interviewers = sum(1 for interviewer in interviewer_risk if interviewer["risk_score"] >= 55)
    analysis_coverage = round(
        (
            sum(
                1
                for entry in data
                if all(field in entry for field in ("reasons_positive", "reasons_negative", "round_type", "style_tags", "key_quote"))
            ) / len(data)
        ) * 100,
        1,
    ) if data else 0

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
        "candidate_outcomes": candidate_outcomes,
        "interviewer_leaderboard": interviewer_leaderboard,
        "round_distribution": round_distribution,
        "has_deep_analysis": has_deep_analysis,
        "decision_funnel": decision_funnel,
        "candidate_review_queue": candidate_review_queue,
        "interviewer_risk": interviewer_risk,
        "role_health": role_health,
        "reason_signals": {
            "positive": positive_signals[:8],
            "negative": negative_signals[:8],
            "blockers": blocker_signals[:8],
        },
        "round_insights": round_insights,
        "cross_round_correlation": cross_round_correlation,
        "round_pair_summary": round_pair_summary,
        "stats": {
            "total_interviews": total,
            "unique_interviewers": unique_interviewers,
            "unique_candidates": unique_candidates,
            "overall_pass_rate": overall_pass_rate,
            "consistency_score": consistency_score,
            "conflicted_candidates": conflicted_candidates,
            "high_risk_interviewers": high_risk_interviewers,
            "analysis_coverage": analysis_coverage,
        },
    }


def build_llm_analytics_context(data):
    """Build a compact analytics context for chat and deck generation."""
    analytics = compute_analytics(data)
    payload = {
        "stats": analytics.get("stats", {}),
        "executive_summary": analytics.get("executive_summary", ""),
        "top_insights": analytics.get("top_insights", [])[:5],
        "candidate_review_queue": analytics.get("candidate_review_queue", [])[:8],
        "interviewer_risk": analytics.get("interviewer_risk", [])[:8],
        "role_health": analytics.get("role_health", [])[:8],
        "reason_signals": analytics.get("reason_signals", {}),
        "round_insights": analytics.get("round_insights", [])[:8],
        "red_flags": analytics.get("red_flags", [])[:8],
        "sample_entries": [
            {
                "candidate": entry.get("candidate"),
                "interviewer": entry.get("interviewer"),
                "role": entry.get("role"),
                "decision": entry.get("decision"),
                "score": entry.get("score"),
                "round_type": entry.get("round_type"),
                "reasons_positive": entry.get("reasons_positive", [])[:3],
                "reasons_negative": entry.get("reasons_negative", [])[:3],
                "key_quote": entry.get("key_quote", "")[:180],
            }
            for entry in data[:12]
        ],
    }
    return analytics, json.dumps(payload, ensure_ascii=False, indent=2)


def _tokenize_query(text):
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_+-]{2,}", (text or "").lower())
        if token not in {
            "what", "why", "when", "where", "which", "show", "more", "about", "with", "from",
            "that", "this", "them", "they", "their", "there", "overall", "status", "please",
            "candidate", "candidates", "interviewer", "interviewers",
        }
    }


def _rank_entry_relevance(entry, query_text):
    haystack = " ".join([
        str(entry.get("candidate", "")),
        str(entry.get("interviewer", "")),
        str(entry.get("role", "")),
        str(entry.get("decision", "")),
        str(entry.get("round_type", "")),
        " ".join(entry.get("reasons_positive", [])[:4]),
        " ".join(entry.get("reasons_negative", [])[:4]),
        str(entry.get("key_quote", "")),
        str(entry.get("feedback_text", ""))[:240],
    ]).lower()
    score = 0
    for token in _tokenize_query(query_text):
        if token in haystack:
            score += 1
    return score


def build_chat_context(data, query_text="", history=None):
    analytics = compute_analytics(data)
    combined_query = " ".join(
        [query_text or ""] + [turn.get("content", "") for turn in (history or [])[-4:]]
    )
    ranked_entries = sorted(
        data,
        key=lambda entry: (_rank_entry_relevance(entry, combined_query), entry.get("date", "")),
        reverse=True,
    )
    relevant_entries = [
        {
            "candidate": entry.get("candidate"),
            "interviewer": entry.get("interviewer"),
            "role": entry.get("role"),
            "decision": entry.get("decision"),
            "score": entry.get("score"),
            "round_type": entry.get("round_type"),
            "reasons_positive": entry.get("reasons_positive", [])[:2],
            "reasons_negative": entry.get("reasons_negative", [])[:2],
            "key_quote": entry.get("key_quote", "")[:140],
        }
        for entry in ranked_entries[:6]
        if _rank_entry_relevance(entry, combined_query) > 0
    ]

    payload = {
        "query": query_text,
        "stats": analytics.get("stats", {}),
        "executive_summary": analytics.get("executive_summary", ""),
        "top_insights": analytics.get("top_insights", [])[:3],
        "red_flags": analytics.get("red_flags", [])[:4],
        "candidate_review_queue": analytics.get("candidate_review_queue", [])[:4],
        "interviewer_risk": analytics.get("interviewer_risk", [])[:5],
        "role_health": analytics.get("role_health", [])[:3],
        "round_insights": analytics.get("round_insights", [])[:4],
        "reason_signals": {
            "positive": analytics.get("reason_signals", {}).get("positive", [])[:4],
            "negative": analytics.get("reason_signals", {}).get("negative", [])[:4],
            "blockers": analytics.get("reason_signals", {}).get("blockers", [])[:4],
        },
        "relevant_entries": relevant_entries,
    }
    return analytics, json.dumps(payload, ensure_ascii=False, indent=2)


def build_deck_context(data):
    analytics = compute_analytics(data)
    payload = {
        "topic_summary": analytics.get("executive_summary", ""),
        "stats": analytics.get("stats", {}),
        "top_insights": analytics.get("top_insights", [])[:4],
        "red_flags": analytics.get("red_flags", [])[:4],
        "interviewer_risk": [
            {
                "interviewer": item.get("interviewer") or item.get("name"),
                "pass_rate": item.get("pass_rate"),
                "risk_score": item.get("risk_score"),
                "agreement_gap": item.get("agreement_gap") or item.get("disagreement_rate"),
                "top_blockers": item.get("top_blockers", [])[:2] or ([item.get("top_negative_reason")] if item.get("top_negative_reason") else []),
            }
            for item in analytics.get("interviewer_risk", [])[:5]
        ],
        "role_health": [
            {
                "role": item.get("role"),
                "pass_rate": item.get("pass_rate"),
                "calibration_spread": item.get("calibration_spread"),
                "top_blockers": item.get("top_blockers", [])[:3],
                "top_supports": item.get("top_supports", [])[:2],
            }
            for item in analytics.get("role_health", [])[:4]
        ],
        "round_insights": analytics.get("round_insights", [])[:5],
        "reason_signals": {
            "positive": analytics.get("reason_signals", {}).get("positive", [])[:4],
            "negative": analytics.get("reason_signals", {}).get("negative", [])[:4],
            "blockers": analytics.get("reason_signals", {}).get("blockers", [])[:4],
        },
    }
    return analytics, json.dumps(payload, ensure_ascii=False, indent=2)


def _filter_entries_from_request(entries):
    role = request.args.get("role")
    interviewer = request.args.get("interviewer")
    decision = request.args.get("decision")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    filtered = entries[:]
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
    return filtered


def _clean_deck_spec(spec, fallback):
    if not isinstance(spec, dict):
        return fallback
    title = str(spec.get("title") or fallback["title"])[:120]
    subtitle = str(spec.get("subtitle") or fallback.get("subtitle", ""))[:280]
    cleaned_slides = []
    for slide in spec.get("slides", []):
        if not isinstance(slide, dict):
            continue
        bullets = [str(item)[:220] for item in slide.get("bullets", []) if str(item).strip()][:6]
        stats = []
        for item in slide.get("stats", []):
            if isinstance(item, dict):
                stats.append({
                    "label": str(item.get("label", ""))[:40],
                    "value": str(item.get("value", ""))[:40],
                })
        cleaned_slides.append({
            "title": str(slide.get("title", "Untitled Slide"))[:120],
            "kicker": str(slide.get("kicker", ""))[:120],
            "bullets": bullets,
            "stats": stats[:4],
        })
    if not cleaned_slides:
        return fallback
    return {"title": title, "subtitle": subtitle, "slides": cleaned_slides[:8]}


def _deck_spec_is_valid(spec):
    if not isinstance(spec, dict):
        return False
    slides = spec.get("slides")
    if not isinstance(slides, list) or not (5 <= len(slides) <= 7):
        return False
    for slide in slides:
        if not isinstance(slide, dict):
            return False
        title = str(slide.get("title", "")).strip()
        bullets = [str(item).strip() for item in slide.get("bullets", []) if str(item).strip()]
        if not title or len(bullets) < 2:
            return False
    return True


def _build_deck_prompt(topic, context_json):
    return (
        "You are an executive presentation strategist creating a premium HTML briefing deck for hiring leaders. "
        "Return ONLY valid JSON. No markdown fences. No explanation text. "
        "The JSON must exactly match this shape: "
        '{"title":"...","subtitle":"...","slides":[{"title":"...","kicker":"...","bullets":["..."],"stats":[{"label":"...","value":"..."}]}]}. '
        "Rules: produce between 5 and 7 slides inclusive; each slide must make one strong point; every slide must have 2 to 4 bullets; "
        "at least 4 slides must include 2 to 4 stats; bullets must be concrete, evidence-based, and presentation-ready; "
        "title and kicker should be crisp, not generic. "
        f"Topic: {topic}\n\n"
        f"Analytics context:\n{context_json}\n"
    )


def _fallback_deck_spec(topic, analytics):
    stats = analytics.get("stats", {})
    top_insights = analytics.get("top_insights", [])
    interviewer_risk = analytics.get("interviewer_risk", [])
    role_health = analytics.get("role_health", [])
    round_insights = analytics.get("round_insights", [])
    red_flags = analytics.get("red_flags", [])
    blockers = analytics.get("reason_signals", {}).get("blockers", [])

    strictest = interviewer_risk[0] if interviewer_risk else {}
    most_lenient = interviewer_risk[-1] if interviewer_risk else {}
    weakest_role = role_health[0] if role_health else {}
    noisiest_round = min(round_insights, key=lambda item: item.get("pass_rate", 100)) if round_insights else {}
    strictest_name = strictest.get("interviewer") or strictest.get("name") or "Strict interviewer"
    lenient_name = most_lenient.get("interviewer") or most_lenient.get("name") or "N/A"
    agreement_gap = strictest.get("agreement_gap")
    if agreement_gap in (None, ""):
        agreement_gap = strictest.get("disagreement_rate", 0)

    slides = [
        {
            "title": "Overall status is productive but unstable",
            "kicker": "Status",
            "bullets": [
                f"The dataset covers {stats.get('total_interviews', 0)} interviews across {stats.get('unique_candidates', 0)} candidates and {stats.get('unique_interviewers', 0)} interviewers.",
                f"Overall pass rate sits at {stats.get('overall_pass_rate', 0)}%, but consistency is only {stats.get('consistency_score', 0)}/100.",
                f"{stats.get('conflicted_candidates', 0)} candidates land in the review queue, which signals unresolved calibration noise rather than simple throughput problems.",
            ],
            "stats": [
                {"label": "Interviews", "value": str(stats.get("total_interviews", 0))},
                {"label": "Candidates", "value": str(stats.get("unique_candidates", 0))},
                {"label": "Pass Rate", "value": f"{stats.get('overall_pass_rate', 0)}%"},
                {"label": "Consistency", "value": f"{stats.get('consistency_score', 0)}/100"},
            ],
        },
        {
            "title": "Interviewer calibration is the main source of risk",
            "kicker": "Calibration",
            "bullets": [
                top_insights[0] if len(top_insights) > 0 else "The strictness spread across interviewers is materially affecting outcomes.",
                top_insights[1] if len(top_insights) > 1 else "Leniency outliers exist alongside very strict interviewers.",
                top_insights[2] if len(top_insights) > 2 else "Shared-candidate disagreement is high enough to justify calibration sessions.",
            ],
            "stats": [
                {"label": "High-Risk Interviewers", "value": str(stats.get("high_risk_interviewers", 0))},
                {"label": "Review Queue", "value": str(stats.get("conflicted_candidates", 0))},
                {"label": "Strictest", "value": strictest_name},
                {"label": "Lenient Edge", "value": lenient_name},
            ],
        },
        {
            "title": f"{strictest_name} is setting the lowest bar for passing",
            "kicker": "Interviewer Profile",
            "bullets": [
                f"Pass rate is {strictest.get('pass_rate', 0)}% with a risk score of {strictest.get('risk_score', 0)}.",
                f"Agreement gap versus team baseline is {agreement_gap} points, which suggests this is not random noise.",
                f"Repeated blockers include {', '.join(strictest.get('top_blockers', [])[:2]) or 'communication and technical depth concerns'}.",
            ],
            "stats": [
                {"label": "Pass Rate", "value": f"{strictest.get('pass_rate', 0)}%"},
                {"label": "Risk Score", "value": str(strictest.get("risk_score", 0))},
                {"label": "Avg Score", "value": str(strictest.get("avg_score", 0))},
                {"label": "Candidates Flagged", "value": str(strictest.get("flagged_candidates", 0))},
            ],
        },
        {
            "title": f"{weakest_role.get('role', 'Core pipeline')} is where process quality breaks down most",
            "kicker": "Role Health",
            "bullets": [
                f"Pass rate is {weakest_role.get('pass_rate', 0)}% with calibration spread at {weakest_role.get('calibration_spread', 0)}.",
                f"Top blockers are {', '.join(weakest_role.get('top_blockers', [])[:3]) or 'technical and communication issues'}.",
                f"Review pressure is concentrated here, so any calibration fix should start with this role first.",
            ],
            "stats": [
                {"label": "Role", "value": weakest_role.get("role", "N/A")},
                {"label": "Pass Rate", "value": f"{weakest_role.get('pass_rate', 0)}%"},
                {"label": "Spread", "value": str(weakest_role.get("calibration_spread", 0))},
                {"label": "Reviews", "value": str(weakest_role.get("review_count", 0))},
            ],
        },
        {
            "title": f"{noisiest_round.get('round_type', 'One round')} is producing the weakest signal quality",
            "kicker": "Round Design",
            "bullets": [
                f"Pass rate is {noisiest_round.get('pass_rate', 0)}% with average score {noisiest_round.get('avg_score', 0)}.",
                f"The dominant blocker is {noisiest_round.get('top_blocker', 'unclear')}, while the top positive signal is {noisiest_round.get('top_signal', 'unclear')}.",
                "This round likely needs tighter rubrics or better interviewer calibration to produce cleaner downstream decisions.",
            ],
            "stats": [
                {"label": "Round", "value": noisiest_round.get("round_type", "N/A")},
                {"label": "Pass Rate", "value": f"{noisiest_round.get('pass_rate', 0)}%"},
                {"label": "Avg Score", "value": str(noisiest_round.get("avg_score", 0))},
                {"label": "Volume", "value": str(noisiest_round.get("count", 0))},
            ],
        },
        {
            "title": "Action should focus on calibration, not just more candidate volume",
            "kicker": "Recommended Action",
            "bullets": [
                red_flags[0]["description"] if red_flags else "Run a calibration review on the most extreme interviewer outliers.",
                "Review 5 to 10 disputed candidates together and align on what counts as a hire versus a no-hire.",
                f"Normalize repeated blocker definitions such as {', '.join(item.get('reason', '') for item in blockers[:2]) or 'communication and technical depth'} so scorecards use the same language.",
            ],
            "stats": [
                {"label": "Priority", "value": "Calibration"},
                {"label": "First Scope", "value": weakest_role.get("role", "Top role")},
                {"label": "Disputes", "value": str(stats.get("conflicted_candidates", 0))},
                {"label": "Coverage", "value": f"{stats.get('analysis_coverage', 0)}%"},
            ],
        },
    ]

    return {
        "title": topic,
        "subtitle": analytics.get("executive_summary", ""),
        "slides": slides[:6],
    }


def _generate_validated_deck_spec(topic, analytics, context_json):
    fallback = {
        "title": topic,
        "subtitle": analytics.get("executive_summary", ""),
        "slides": [],
    }
    prompt = _build_deck_prompt(topic, context_json)
    errors = []

    for attempt in range(2):
        try:
            raw = run_llm_prompt(prompt, timeout=40)
        except Exception as exc:
            errors.append(f"attempt {attempt + 1}: {exc}")
            prompt = (
                "Return ONLY valid JSON for a 5 to 7 slide deck. Keep the output brief and structured.\n\n"
                f"Topic: {topic}\n\n"
                f"Analytics context:\n{context_json}\n"
            )
            continue
        parsed = _extract_json_from_response(raw)
        cleaned = _clean_deck_spec(parsed, fallback)
        if _deck_spec_is_valid(cleaned):
            return cleaned

        slide_count = len(cleaned.get("slides", [])) if isinstance(cleaned, dict) else 0
        errors.append(f"attempt {attempt + 1}: invalid deck spec with {slide_count} slides")
        prompt = (
            "Repair the previous deck response. Return ONLY valid JSON and satisfy every rule exactly. "
            "You must return 5 to 7 slides. Each slide must have a real title and 2 to 4 bullets. "
            "Preserve the topic and the evidence from the analytics context.\n\n"
            f"Topic: {topic}\n\n"
            f"Analytics context:\n{context_json}\n\n"
            f"Previous invalid response:\n{raw}\n"
        )

    return _fallback_deck_spec(topic, analytics)


def render_deck_html(spec):
    """Render a presentation-grade HTML deck."""
    title = spec.get("title", "HireSignal Briefing")
    subtitle = spec.get("subtitle", "")
    slides_html = []
    for index, slide in enumerate(spec.get("slides", []), start=1):
        stats_html = ""
        if slide.get("stats"):
            stats_html = '<div class="deck-stats">' + "".join(
                f'<div class="deck-stat"><span class="deck-stat-label">{item["label"]}</span><span class="deck-stat-value">{item["value"]}</span></div>'
                for item in slide["stats"]
            ) + "</div>"
        bullets_html = "".join(f"<li>{bullet}</li>" for bullet in slide.get("bullets", []))
        slides_html.append(f"""
        <section class="slide">
          <div class="slide-index">{index:02d}</div>
          <div class="slide-shell">
            <div class="slide-kicker">{slide.get('kicker', '')}</div>
            <h2>{slide.get('title', '')}</h2>
            {stats_html}
            <ul class="slide-bullets">{bullets_html}</ul>
          </div>
        </section>
        """)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    :root {{
      --bg: #09111f;
      --bg-soft: #0f1b31;
      --card: rgba(255,255,255,0.08);
      --line: rgba(255,255,255,0.14);
      --text: #f6f7fb;
      --muted: #9fb1ca;
      --blue: #69a3ff;
      --green: #72dfb3;
      --gold: #f0c36b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
      background:
        radial-gradient(circle at top left, rgba(105,163,255,0.18), transparent 24%),
        radial-gradient(circle at bottom right, rgba(114,223,179,0.16), transparent 22%),
        linear-gradient(180deg, #08101d, #0a1628 46%, #0c1a30);
      color: var(--text);
    }}
    .deck-cover {{
      min-height: 100vh;
      padding: 72px;
      display: grid;
      align-items: end;
      border-bottom: 1px solid var(--line);
    }}
    .deck-cover-inner {{
      max-width: 980px;
    }}
    .deck-eyebrow {{
      display: inline-block;
      margin-bottom: 18px;
      padding: 8px 14px;
      border-radius: 999px;
      background: rgba(105,163,255,0.12);
      color: var(--blue);
      font: 700 12px/1.2 ui-sans-serif, system-ui, sans-serif;
      text-transform: uppercase;
      letter-spacing: 0.14em;
    }}
    .deck-cover h1 {{
      margin: 0;
      font-size: clamp(52px, 8vw, 92px);
      line-height: 0.94;
      letter-spacing: -0.04em;
      max-width: 10ch;
    }}
    .deck-cover p {{
      max-width: 760px;
      margin-top: 22px;
      color: var(--muted);
      font-size: 22px;
      line-height: 1.55;
    }}
    .slides {{
      padding: 36px;
      display: grid;
      gap: 28px;
    }}
    .slide {{
      min-height: 92vh;
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 32px;
      background:
        linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02)),
        rgba(10, 20, 36, 0.86);
      position: relative;
      overflow: hidden;
      display: grid;
      align-items: stretch;
    }}
    .slide::before {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        radial-gradient(circle at top right, rgba(105,163,255,0.16), transparent 26%),
        radial-gradient(circle at bottom left, rgba(240,195,107,0.10), transparent 24%);
      pointer-events: none;
    }}
    .slide-index {{
      position: absolute;
      top: 28px;
      right: 32px;
      font: 700 12px/1.2 ui-sans-serif, system-ui, sans-serif;
      color: rgba(255,255,255,0.4);
      letter-spacing: 0.18em;
    }}
    .slide-shell {{
      position: relative;
      z-index: 1;
      max-width: 1100px;
      padding: 24px 8px 8px;
    }}
    .slide-kicker {{
      font: 700 12px/1.2 ui-sans-serif, system-ui, sans-serif;
      text-transform: uppercase;
      letter-spacing: 0.18em;
      color: var(--gold);
      margin-bottom: 18px;
    }}
    .slide h2 {{
      margin: 0 0 24px;
      max-width: 12ch;
      font-size: clamp(36px, 5vw, 64px);
      line-height: 0.98;
      letter-spacing: -0.04em;
    }}
    .deck-stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 16px;
      margin: 18px 0 28px;
    }}
    .deck-stat {{
      padding: 18px 20px;
      border-radius: 20px;
      background: var(--card);
      border: 1px solid rgba(255,255,255,0.09);
      backdrop-filter: blur(8px);
    }}
    .deck-stat-label {{
      display: block;
      font: 700 11px/1.2 ui-sans-serif, system-ui, sans-serif;
      color: var(--muted);
      letter-spacing: 0.14em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    .deck-stat-value {{
      display: block;
      font-size: 34px;
      line-height: 1;
      letter-spacing: -0.04em;
    }}
    .slide-bullets {{
      margin: 0;
      padding-left: 22px;
      display: grid;
      gap: 18px;
      max-width: 980px;
      font-size: 24px;
      line-height: 1.45;
      color: #eef3fb;
    }}
    .slide-bullets li::marker {{
      color: var(--green);
    }}
    @media print {{
      .slide {{
        break-after: page;
        min-height: 100vh;
      }}
    }}
  </style>
</head>
<body>
  <header class="deck-cover">
    <div class="deck-cover-inner">
      <span class="deck-eyebrow">HireSignal Briefing</span>
      <h1>{title}</h1>
      <p>{subtitle}</p>
    </div>
  </header>
  <main class="slides">
    {''.join(slides_html)}
  </main>
</body>
</html>"""


def save_deck_html(title, html):
    ensure_decks_dir()
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "deck").lower()).strip("-")[:48] or "deck"
    filename = f"{int(time.time())}-{slug}.html"
    filepath = os.path.join(DECKS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return filename


def list_saved_decks(limit=20):
    ensure_decks_dir()
    decks = []
    for filepath in sorted(glob.glob(os.path.join(DECKS_DIR, "*.html")), reverse=True)[:limit]:
        stat = os.stat(filepath)
        filename = os.path.basename(filepath)
        decks.append({
            "filename": filename,
            "url": f"/decks/{filename}",
            "title": filename.rsplit(".", 1)[0].split("-", 1)[-1].replace("-", " ").strip() or filename,
            "updated_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "size_kb": round(stat.st_size / 1024, 1),
        })
    return decks


# --- Routes ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def get_data():
    active_entries = get_active_entries()
    # Deep analysis is triggered explicitly via /api/analyze, not on every data fetch

    role = request.args.get("role")
    interviewer = request.args.get("interviewer")
    decision = request.args.get("decision")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    filtered = active_entries[:]
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

    payload = compute_analytics(filtered)
    payload["dataset_state"] = build_dataset_summary()
    return jsonify(payload)


@app.route("/api/chat", methods=["POST"])
def chat():
    active_entries = get_active_entries()
    body = request.get_json(silent=True) or {}
    message = str(body.get("message", "")).strip()
    chat_session_id = str(body.get("chat_session_id", "")).strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400

    filtered = active_entries[:]
    filters = body.get("filters", {}) if isinstance(body.get("filters"), dict) else {}
    for key, value in filters.items():
        if not value:
            continue
        if key == "role":
            filtered = [e for e in filtered if e["role"] == value]
        elif key == "interviewer":
            filtered = [e for e in filtered if e["interviewer"] == value]
        elif key == "decision":
            filtered = [e for e in filtered if e["decision"] == value]
        elif key == "date_from":
            filtered = [e for e in filtered if e.get("date", "") >= value]
        elif key == "date_to":
            filtered = [e for e in filtered if e.get("date", "") <= value]

    session = get_chat_session(chat_session_id)
    history = []
    if session:
        history = session.get("turns", [])[-8:]
    analytics, context_json = build_chat_context(filtered, message, history)
    history_text = ""
    if history:
        history_text = "Conversation so far:\n" + "\n".join(
            f"{turn['role'].title()}: {turn['content']}" for turn in history
        ) + "\n\n"
    prompt = (
        "You are a hiring analytics copilot. Answer the user's question using only the analytics context provided. "
        "Be concise, concrete, and decision-oriented. Reference actual names, roles, and repeated blockers where useful. "
        "If the user asks a follow-up like 'why', 'who', 'show me more', or 'what about them', resolve it from the conversation history. "
        "If evidence is weak, say so plainly. Use markdown with short paragraphs or flat bullets.\n\n"
        f"{history_text}"
        f"Analytics context:\n{context_json}\n\n"
        f"User question: {message}\n\n"
        "Answer now:"
    )
    try:
        answer = run_llm_prompt(prompt, timeout=120)
        if not answer.strip():
            raise ValueError("Empty answer from LLM")
    except Exception as exc:
        return jsonify({"error": f"Copilot could not get a model response: {exc}"}), 502
    if session is not None:
        session["turns"].append({"role": "user", "content": message})
        session["turns"].append({"role": "assistant", "content": answer.strip()})
        session["updated_at"] = time.time()
        _trim_chat_sessions()
    return jsonify({"answer": answer})


@app.route("/api/chat/reset", methods=["POST"])
def reset_chat():
    body = request.get_json(silent=True) or {}
    chat_session_id = str(body.get("chat_session_id", "")).strip()
    if chat_session_id:
        chat_sessions.pop(chat_session_id, None)
    return jsonify({"status": "cleared"})


@app.route("/api/deck", methods=["POST"])
def generate_deck():
    active_entries = get_active_entries()
    body = request.get_json(silent=True) or {}
    topic = str(body.get("topic", "")).strip() or "Interview Process Review"
    filtered = active_entries[:]
    filters = body.get("filters", {}) if isinstance(body.get("filters"), dict) else {}
    for key, value in filters.items():
        if not value:
            continue
        if key == "role":
            filtered = [e for e in filtered if e["role"] == value]
        elif key == "interviewer":
            filtered = [e for e in filtered if e["interviewer"] == value]
        elif key == "decision":
            filtered = [e for e in filtered if e["decision"] == value]
        elif key == "date_from":
            filtered = [e for e in filtered if e.get("date", "") >= value]
        elif key == "date_to":
            filtered = [e for e in filtered if e.get("date", "") <= value]

    analytics, context_json = build_deck_context(filtered)
    try:
        spec = _generate_validated_deck_spec(topic, analytics, context_json)
    except Exception as exc:
        return jsonify({"error": f"Deck generation failed before a valid model response was produced: {exc}"}), 502
    html = render_deck_html(spec)
    filename = save_deck_html(spec.get("title", topic), html)
    return jsonify({
        "html": html,
        "title": spec.get("title", "HireSignal Briefing"),
        "slide_count": len(spec.get("slides", [])),
        "deck_url": f"/decks/{filename}",
        "deck_file": filename,
    })


@app.route("/decks/<path:filename>")
def serve_deck(filename):
    ensure_decks_dir()
    safe_name = os.path.basename(filename)
    if not safe_name or safe_name != filename:
        return jsonify({"error": "Invalid filename"}), 400
    return send_from_directory(DECKS_DIR, safe_name)


@app.route("/api/decks")
def list_decks():
    return jsonify(list_saved_decks())


@app.route("/api/decks/<path:filename>", methods=["DELETE"])
def delete_deck(filename):
    ensure_decks_dir()
    safe_name = os.path.basename(filename)
    if not safe_name or safe_name != filename:
        return jsonify({"error": "Invalid filename"}), 400
    filepath = os.path.join(DECKS_DIR, safe_name)
    if not os.path.isfile(filepath):
        return jsonify({"error": "Deck not found"}), 404
    os.remove(filepath)
    return jsonify({"status": "deleted"})


@app.route("/api/narrative", methods=["POST"])
def generate_narrative():
    """Generate an LLM-powered executive narrative from current analytics."""
    active_entries = get_active_entries()
    analytics = compute_analytics(active_entries)
    stats = analytics.get("stats", {})
    summary = analytics.get("executive_summary", "")
    leaderboard = analytics.get("interviewer_leaderboard", [])
    outcomes = analytics.get("candidate_outcomes", [])
    red_flags = analytics.get("red_flags", [])

    if not active_entries:
        return jsonify({"narrative": "No data available to generate a narrative."})

    # Build a context string for the LLM
    context_parts = [
        f"Summary: {summary}",
        f"Total interviews: {stats.get('total_interviews', 0)}, "
        f"Interviewers: {stats.get('unique_interviewers', 0)}, "
        f"Candidates: {stats.get('unique_candidates', 0)}, "
        f"Pass rate: {stats.get('overall_pass_rate', 0)}%, "
        f"Consistency: {stats.get('consistency_score', 0)}/100.",
    ]
    if leaderboard:
        lb_str = "; ".join(
            f"{i['name']}: {i['pass_rate']}% pass rate, avg score {i['avg_score']}/5{' (' + i['label'] + ')' if i['label'] else ''}"
            for i in leaderboard
        )
        context_parts.append(f"Interviewer leaderboard: {lb_str}")
    if outcomes:
        oc_str = "; ".join(
            f"{o['candidate']} ({o['role']}): consensus={o['consensus']}, avg_score={o['avg_score']}"
            for o in outcomes[:10]
        )
        context_parts.append(f"Candidate outcomes: {oc_str}")
    if red_flags:
        rf_str = "; ".join(f["description"] for f in red_flags[:5])
        context_parts.append(f"Red flags: {rf_str}")

    context = "\n".join(context_parts)

    prompt = (
        "You are an executive hiring analytics advisor. Based on the following interview feedback data, "
        "write a 3-4 paragraph executive narrative summary. Cover: (1) Overall hiring bar and quality of candidate pipeline, "
        "(2) Interviewer calibration concerns or strengths, (3) Standout candidates or patterns, "
        "(4) Actionable recommendations. Be specific with names and numbers. Keep it professional and concise.\n\n"
        f"Data:\n{context}\n\n"
        "Write the narrative now (plain text, no markdown headers):"
    )

    try:
        narrative = run_llm_prompt(prompt, timeout=120)
        if narrative and len(narrative) > 50:
            return jsonify({"narrative": narrative})
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as exc:
        print(f"Narrative generation failed ({exc}), using template summary")

    # Fallback to template summary
    return jsonify({"narrative": summary})


def _run_upload_job(job_id, files_data, dataset_mode, dataset_name):
    """Background worker: parse files and ingest. Updates upload_jobs[job_id]."""
    job = upload_jobs[job_id]
    batch_entries = []
    errors = []
    total_files = len(files_data)

    for i, (filename, file_bytes_or_text, is_pdf) in enumerate(files_data):
        job["message"] = f"Parsing {filename}…" + (" (AI reading PDF)" if is_pdf else "")
        job["progress"] = int((i / total_files) * 80)
        try:
            if is_pdf:
                entries = parse_pdf_feedback(file_bytes_or_text)
            else:
                entries = parse_file(filename, file_bytes_or_text)
            batch_entries.extend(entries)
        except Exception as e:
            errors.append(f"{filename}: {str(e)}")

    job["message"] = "Saving entries…"
    job["progress"] = 90
    ingest_result = ingest_grouped_entries(
        batch_entries,
        dataset_mode=dataset_mode,
        dataset_name=dataset_name or f"Upload {_dataset_timestamp()}",
        source="pdf_upload",
        split_mode="none",
    )
    job["status"] = "done"
    job["progress"] = 100
    job["message"] = f"Done — {ingest_result['entries_added']} entries added"
    job["result"] = {
        "added": ingest_result["entries_added"],
        "total": len(feedback_store),
        "active_dataset_id": active_dataset_id,
        "errors": errors,
    }


@app.route("/api/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        return jsonify({"error": "No files provided"}), 400

    dataset_mode = (request.form.get("dataset_mode") or "new").strip().lower()
    dataset_name = (request.form.get("dataset_name") or "").strip()

    ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv", ".json", ".md"}

    # Read all file data eagerly before handing off to thread
    files_data = []
    for f in request.files.getlist("files"):
        if not f.filename:
            continue
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({"error": f"File type '{ext}' not allowed. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"}), 400
        is_pdf = ext == ".pdf"
        if is_pdf:
            files_data.append((f.filename, f.read(), True))
        else:
            files_data.append((f.filename, f.read().decode("utf-8", errors="replace"), False))

    if not files_data:
        return jsonify({"error": "No valid files provided"}), 400

    has_pdf = any(is_pdf for _, _, is_pdf in files_data)
    job_id = str(uuid.uuid4())
    upload_jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "message": "Starting…",
        "result": None,
    }

    t = threading.Thread(target=_run_upload_job, args=(job_id, files_data, dataset_mode, dataset_name), daemon=True)
    t.start()

    return jsonify({
        "job_id": job_id,
        "async": True,
        "has_pdf": has_pdf,
        "message": "Processing started",
    })


@app.route("/api/upload/status/<job_id>")
def upload_status(job_id):
    job = upload_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/paste", methods=["POST"])
def paste():
    global feedback_store
    body = request.get_json(silent=True) or {}
    text = body.get("text", "")
    if not text.strip():
        return jsonify({"error": "No text provided"}), 400

    dataset_mode = str(body.get("dataset_mode", "new")).strip().lower()
    dataset_name = str(body.get("dataset_name", "")).strip()
    entries = parse_file("paste.txt", text)
    ingest_result = ingest_grouped_entries(
        entries,
        dataset_mode=dataset_mode,
        dataset_name=dataset_name or f"Pasted Feedback {_dataset_timestamp()}",
        source="manual",
        split_mode="none",
    )
    return jsonify({"added": ingest_result["entries_added"], "total": len(feedback_store), "active_dataset_id": active_dataset_id})


@app.route("/api/reset", methods=["POST"])
def reset():
    global feedback_store
    feedback_store = load_sample_data()
    rebuild_dataset_registry()
    set_active_dataset("all")
    return jsonify({"status": "reset", "total": len(feedback_store)})


# --- Session Persistence ---

SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "data", "sessions")


def ensure_sessions_dir():
    os.makedirs(SESSIONS_DIR, exist_ok=True)


def auto_save():
    """Auto-save current feedback store after data changes."""
    ensure_sessions_dir()
    filename = f"session_{int(time.time())}.json"
    filepath = os.path.join(SESSIONS_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(feedback_store, f)


@app.route("/api/save", methods=["POST"])
def save_session():
    ensure_sessions_dir()
    filename = f"session_{int(time.time())}.json"
    filepath = os.path.join(SESSIONS_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(feedback_store, f)
    return jsonify({"status": "saved", "filename": filename, "entries": len(feedback_store)})


@app.route("/api/sessions")
def list_sessions():
    ensure_sessions_dir()
    sessions = []
    for filepath in sorted(glob.glob(os.path.join(SESSIONS_DIR, "session_*.json")), reverse=True):
        fname = os.path.basename(filepath)
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            # Extract timestamp from filename
            ts_str = fname.replace("session_", "").replace(".json", "")
            ts = int(ts_str)
            sessions.append({
                "filename": fname,
                "entries": len(data),
                "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp": ts,
            })
        except (json.JSONDecodeError, ValueError, OSError):
            continue
    return jsonify(sessions)


@app.route("/api/sessions/load", methods=["POST"])
def load_session():
    global feedback_store
    body = request.get_json(silent=True) or {}
    filename = os.path.basename(body.get("filename", ""))
    if not filename:
        return jsonify({"error": "Invalid filename"}), 400
    filepath = os.path.join(SESSIONS_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Session not found"}), 404
    with open(filepath, "r") as f:
        feedback_store = json.load(f)
    rebuild_dataset_registry()
    set_active_dataset("all")
    return jsonify({"status": "loaded", "total": len(feedback_store)})


@app.route("/api/sessions/<filename>", methods=["DELETE"])
def delete_session(filename):
    filename = os.path.basename(filename)
    if not filename:
        return jsonify({"error": "Invalid filename"}), 400
    filepath = os.path.join(SESSIONS_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Session not found"}), 404
    os.remove(filepath)
    return jsonify({"status": "deleted"})


@app.route("/api/sessions", methods=["DELETE"])
def delete_all_sessions():
    ensure_sessions_dir()
    for filepath in glob.glob(os.path.join(SESSIONS_DIR, "session_*.json")):
        os.remove(filepath)
    return jsonify({"status": "all_deleted"})


@app.route("/api/clear", methods=["DELETE"])
def clear_data():
    global feedback_store
    feedback_store = load_sample_data()
    rebuild_dataset_registry()
    set_active_dataset("all")
    return jsonify({"status": "cleared", "total": len(feedback_store)})


# --- Deep LLM Analysis Pipeline ---

VALID_ROUND_TYPES = {"take_home_review", "technical_quiz", "technical_interview",
                     "culture_fit", "system_design", "general"}
VALID_STYLE_TAGS = {"structured", "narrative", "concise", "detailed", "bullet_points",
                    "technical_focus", "soft_skills_focus", "balanced"}


def _extract_json_from_response(text):
    """Extract JSON array or object from an LLM response, handling markdown code blocks."""
    if not text:
        return None
    # Try to find JSON in code blocks first
    code_block = re.search(r'```(?:json)?\s*\n?([\s\S]*?)```', text)
    if code_block:
        text = code_block.group(1).strip()
    # Try array
    arr_match = re.search(r'\[[\s\S]*\]', text)
    if arr_match:
        try:
            return json.loads(arr_match.group())
        except json.JSONDecodeError:
            pass
    # Try object
    obj_match = re.search(r'\{[\s\S]*\}', text)
    if obj_match:
        try:
            return json.loads(obj_match.group())
        except json.JSONDecodeError:
            pass
    return None


def _heuristic_analysis(entry):
    """Fallback heuristic-based analysis when LLM is unavailable."""
    text = entry.get("feedback_text", "").lower()
    words = set(re.findall(r'\b\w+\b', text))

    # Positive reasons
    reasons_positive = []
    if words & {"strong", "excellent", "outstanding", "impressive", "solid"}:
        if any(kw in text for kw in ["technical", "algorithm", "system design", "architecture"]):
            reasons_positive.append("Strong technical knowledge")
        if any(kw in text for kw in ["communicat", "articulate", "explain", "clarity"]):
            reasons_positive.append("Good communication skills")
        if any(kw in text for kw in ["problem", "solution", "analytical", "approach"]):
            reasons_positive.append("Strong problem-solving ability")
        if any(kw in text for kw in ["team", "collaborat", "culture"]):
            reasons_positive.append("Good cultural fit")
        if any(kw in text for kw in ["code", "clean", "implement"]):
            reasons_positive.append("Clean coding practices")
    if not reasons_positive and entry.get("sentiment", 0) > 0.2:
        reasons_positive.append("Generally positive assessment")

    # Negative reasons
    reasons_negative = []
    if words & {"weak", "poor", "lacking", "struggled", "unable", "gap", "gaps"}:
        if any(kw in text for kw in ["technical", "algorithm", "database", "architecture"]):
            reasons_negative.append("Gaps in technical knowledge")
        if any(kw in text for kw in ["communicat", "explain", "clarity"]):
            reasons_negative.append("Communication needs improvement")
        if any(kw in text for kw in ["problem", "debug", "approach"]):
            reasons_negative.append("Weak problem-solving approach")
        if any(kw in text for kw in ["code", "implement", "syntax"]):
            reasons_negative.append("Coding ability below expectations")
    if not reasons_negative and entry.get("sentiment", 0) < -0.2:
        reasons_negative.append("Generally negative assessment")

    # Round type
    round_type = "general"
    if any(kw in text for kw in ["take home", "take-home", "homework", "assignment"]):
        round_type = "take_home_review"
    elif any(kw in text for kw in ["quiz", "trivia", "multiple choice"]):
        round_type = "technical_quiz"
    elif any(kw in text for kw in ["system design", "architect", "scalab", "distributed"]):
        round_type = "system_design"
    elif any(kw in text for kw in ["culture", "values", "team fit", "personality"]):
        round_type = "culture_fit"
    elif any(kw in text for kw in ["technical", "coding", "algorithm", "interview"]):
        round_type = "technical_interview"

    # Style tags
    style_tags = []
    sentences = re.split(r'[.!?]+', entry.get("feedback_text", ""))
    avg_sentence_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
    if "- " in entry.get("feedback_text", "") or "• " in entry.get("feedback_text", ""):
        style_tags.append("bullet_points")
    if avg_sentence_len < 10:
        style_tags.append("concise")
    elif avg_sentence_len > 20:
        style_tags.append("detailed")
    if len(entry.get("feedback_text", "")) > 500:
        style_tags.append("narrative")
    else:
        style_tags.append("structured")
    tech_words = sum(1 for w in words if w in {"api", "code", "algorithm", "database", "system", "architecture", "technical"})
    soft_words = sum(1 for w in words if w in {"team", "communication", "culture", "attitude", "personality", "collaborative"})
    if tech_words > soft_words * 2:
        style_tags.append("technical_focus")
    elif soft_words > tech_words * 2:
        style_tags.append("soft_skills_focus")
    else:
        style_tags.append("balanced")
    style_tags = [t for t in style_tags if t in VALID_STYLE_TAGS]

    # Key quote
    orig_sentences = re.split(r'(?<=[.!?])\s+', entry.get("feedback_text", ""))
    key_quote = ""
    for s in orig_sentences:
        s = s.strip()
        if len(s) > 30 and any(w in s.lower() for w in ["strong", "weak", "recommend", "concern", "impressive", "struggled", "excellent", "poor"]):
            key_quote = s[:200]
            break
    if not key_quote and orig_sentences:
        key_quote = orig_sentences[0].strip()[:200]

    return {
        "reasons_positive": reasons_positive,
        "reasons_negative": reasons_negative,
        "round_type": round_type,
        "style_tags": style_tags,
        "key_quote": key_quote,
    }


def _run_deep_analysis(entries):
    """Run LLM-powered deep analysis on a batch of entries. Returns list of analysis dicts."""
    # Build batches of max 10 entries each
    batch_size = 10
    batches = [entries[i:i + batch_size] for i in range(0, len(entries), batch_size)]
    all_results = []

    for batch in batches:
        # Build the prompt with entry texts
        entry_texts = []
        for idx, entry in enumerate(batch):
            entry_texts.append(
                f"--- Entry {idx} ---\n"
                f"ID: {entry.get('id')}\n"
                f"Interviewer: {entry.get('interviewer', 'Unknown')}\n"
                f"Candidate: {entry.get('candidate', 'Unknown')}\n"
                f"Decision: {entry.get('decision', 'unknown')}\n"
                f"Feedback:\n{entry.get('feedback_text', '')[:1500]}\n"
            )

        prompt = (
            "You are an expert interview feedback analyzer. Analyze each feedback entry below and return a JSON array "
            "with one object per entry, in the same order.\n\n"
            "Each object must have these fields:\n"
            '- "entry_id": the ID from the entry\n'
            '- "reasons_positive": list of 2-5 STANDARDIZED positive reasons. Use CONSISTENT wording across entries so identical strengths share the same label. '
            "Choose from patterns like: \"Strong hash/encryption knowledge\", \"Good database/index understanding\", "
            "\"Solid Doctrine ORM skills\", \"Good Git workflow knowledge\", \"Strong PHP fundamentals\", "
            "\"Good communication skills\", \"Strong problem-solving approach\", \"Good code quality\", "
            "\"Business value awareness\", \"DDD/architecture knowledge\", \"Good cultural fit\", "
            "\"Proactive/ownership mindset\". You may create similar standardized labels but REUSE the same label across entries when the reason is the same.\n"
            '- "reasons_negative": list of 2-5 STANDARDIZED negative reasons. Same rule — use CONSISTENT labels. '
            "Choose from patterns like: \"Weak hash/encryption knowledge\", \"Poor database/index understanding\", "
            "\"Lack of Doctrine ORM knowledge\", \"Poor Git rebase understanding\", \"Weak PHP fundamentals\", "
            "\"Poor communication/English\", \"Lacks problem-solving skills\", \"Low code quality\", "
            "\"No business awareness\", \"Passive/low energy\", \"Poor cultural fit\". "
            "REUSE the same label across entries when the weakness is the same.\n"
            '- "round_type": one of ["take_home_review", "technical_quiz", "technical_interview", "culture_fit", "system_design", "general"] '
            '- inferred from the feedback content\n'
            '- "style_tags": list describing the interviewer\'s writing style, chosen from '
            '["structured", "narrative", "concise", "detailed", "bullet_points", "technical_focus", "soft_skills_focus", "balanced"]\n'
            '- "key_quote": the most insightful 1-2 sentence quote from the feedback text (exact quote)\n\n'
            "Return ONLY the JSON array, no other text.\n\n"
            "Entries to analyze:\n\n" + "\n".join(entry_texts)
        )

        try:
            parsed = _extract_json_from_response(run_llm_prompt(prompt, timeout=120))
            if isinstance(parsed, list) and len(parsed) == len(batch):
                all_results.extend(parsed)
                continue
            elif isinstance(parsed, list) and parsed:
                # Partial results — pad with heuristic fallbacks
                all_results.extend(parsed)
                for i in range(len(parsed), len(batch)):
                    all_results.append(None)
                continue
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as exc:
            print(f"Deep analysis LLM call failed ({exc}), using heuristic fallback for batch")

        # Fallback: mark all entries in this batch for heuristic analysis
        all_results.extend([None] * len(batch))

    return all_results


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Run deep LLM-powered analysis on all feedback entries."""
    active_entries = get_active_entries()
    if not active_entries:
        return jsonify({"error": "No feedback data to analyze"}), 400

    results = _run_deep_analysis(active_entries)
    _apply_analysis_results(active_entries, results)
    auto_save()
    return jsonify({"status": "analyzed", "entries": len(active_entries)})


@app.route("/api/reasons")
def get_reasons():
    """Return aggregated reason analysis from enriched feedback data."""
    active_entries = get_active_entries()
    if _needs_deep_analysis(active_entries):
        return jsonify({
            "error": "Deep analysis has not been run for the active dataset yet.",
            "analysis_required": True,
        }), 409

    # Aggregate positive reasons
    positive_reason_data = defaultdict(lambda: {"count": 0, "candidates": set()})
    negative_reason_data = defaultdict(lambda: {"count": 0, "candidates": set()})
    reasons_by_interviewer = defaultdict(lambda: {"positive": [], "negative": []})

    for entry in active_entries:
        candidate = entry.get("candidate", "Unknown")
        interviewer = entry.get("interviewer", "Unknown")
        for reason in entry.get("reasons_positive", []):
            positive_reason_data[reason]["count"] += 1
            positive_reason_data[reason]["candidates"].add(candidate)
            if reason not in reasons_by_interviewer[interviewer]["positive"]:
                reasons_by_interviewer[interviewer]["positive"].append(reason)
        for reason in entry.get("reasons_negative", []):
            negative_reason_data[reason]["count"] += 1
            negative_reason_data[reason]["candidates"].add(candidate)
            if reason not in reasons_by_interviewer[interviewer]["negative"]:
                reasons_by_interviewer[interviewer]["negative"].append(reason)

    top_positive = sorted(
        [{"reason": r, "count": d["count"], "candidates": sorted(d["candidates"])}
         for r, d in positive_reason_data.items()],
        key=lambda x: x["count"], reverse=True,
    )
    top_negative = sorted(
        [{"reason": r, "count": d["count"], "candidates": sorted(d["candidates"])}
         for r, d in negative_reason_data.items()],
        key=lambda x: x["count"], reverse=True,
    )

    # Reason correlations: for each negative reason, compute how often it correlates with no_hire/strong_no_hire
    reason_correlations = []
    for reason in negative_reason_data:
        entries_with = [e for e in active_entries if reason in e.get("reasons_negative", [])]
        if len(entries_with) >= 2:
            no_hires = sum(1 for e in entries_with if e.get("decision") in ("no_hire", "strong_no_hire"))
            pct = round(no_hires / len(entries_with) * 100)
            reason_correlations.append({
                "reason": reason,
                "decision_impact": f"{pct}% no_hire when present",
            })
    reason_correlations.sort(key=lambda x: x["decision_impact"], reverse=True)

    return jsonify({
        "top_positive_reasons": top_positive[:15],
        "top_negative_reasons": top_negative[:15],
        "reasons_by_interviewer": dict(reasons_by_interviewer),
        "reason_correlations": reason_correlations[:15],
    })


@app.route("/api/styles")
def get_styles():
    """Return interviewer style analysis from enriched feedback data."""
    active_entries = get_active_entries()
    if _needs_deep_analysis(active_entries):
        return jsonify({
            "error": "Deep analysis has not been run for the active dataset yet.",
            "analysis_required": True,
        }), 409

    # Group by interviewer
    interviewer_entries = defaultdict(list)
    for entry in active_entries:
        interviewer_entries[entry.get("interviewer", "Unknown")].append(entry)

    profiles = {}
    for name, entries in interviewer_entries.items():
        # Aggregate style tags
        all_tags = []
        for e in entries:
            all_tags.extend(e.get("style_tags", []))
        tag_counts = Counter(all_tags)
        # Top tags (those appearing in >30% of entries)
        threshold = max(1, len(entries) * 0.3)
        top_tags = [tag for tag, count in tag_counts.most_common() if count >= threshold]
        if not top_tags:
            top_tags = [tag_counts.most_common(1)[0][0]] if tag_counts else ["balanced"]

        # Average feedback length
        lengths = [len(e.get("feedback_text", "")) for e in entries]
        avg_len = round(sum(lengths) / len(lengths)) if lengths else 0

        # Focus areas (from themes)
        all_themes = []
        for e in entries:
            all_themes.extend(e.get("themes", []))
        theme_counts = Counter(all_themes)
        focus_areas = [t for t, _ in theme_counts.most_common(3)]

        # Tone: based on average sentiment
        sentiments = [e.get("sentiment", 0) for e in entries]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        if avg_sentiment > 0.3:
            tone = "positive"
        elif avg_sentiment < -0.3:
            tone = "critical"
        elif avg_sentiment < 0:
            tone = "cautious"
        else:
            tone = "neutral"

        # Sample quote
        sample_quote = ""
        for e in entries:
            q = e.get("key_quote", "")
            if q and len(q) > 20:
                sample_quote = q
                break

        # Consistency: how consistent are the style tags across entries
        if len(entries) > 1:
            per_entry_tags = [set(e.get("style_tags", [])) for e in entries]
            # Jaccard similarity between consecutive entries
            similarities = []
            for i in range(len(per_entry_tags) - 1):
                a, b = per_entry_tags[i], per_entry_tags[i + 1]
                if a | b:
                    similarities.append(len(a & b) / len(a | b))
            consistency = round(sum(similarities) / len(similarities), 2) if similarities else 0.5
        else:
            consistency = 1.0

        profiles[name] = {
            "style_tags": top_tags,
            "avg_feedback_length": avg_len,
            "focus_areas": focus_areas,
            "tone": tone,
            "sample_quote": sample_quote,
            "consistency": consistency,
        }

    return jsonify({"profiles": profiles})


# --- Interviewer & Role Detail Endpoints ---

@app.route("/api/interviewer/<name>")
def get_interviewer(name):
    entries = [e for e in get_active_entries() if e["interviewer"] == name]
    if not entries:
        return jsonify({"error": "Interviewer not found"}), 404
    analytics = compute_analytics(entries)
    stats = analytics["per_interviewer"].get(name, {})
    stats["entries"] = entries
    stats["name"] = name
    return jsonify(stats)


@app.route("/api/role/<name>")
def get_role(name):
    entries = [e for e in get_active_entries() if e["role"] == name]
    if not entries:
        return jsonify({"error": "Role not found"}), 404
    analytics = compute_analytics(entries)
    role_stats = analytics["per_role"].get(name, {})
    role_stats["entries"] = entries
    role_stats["name"] = name
    role_stats["per_interviewer"] = analytics["per_interviewer"]
    return jsonify(role_stats)


# --- Greenhouse Integration Endpoints ---

@app.route("/api/greenhouse/connect", methods=["POST"])
def greenhouse_connect():
    """Connect to Greenhouse Harvest API or load a realistic mock payload."""
    global greenhouse_state, greenhouse_api_key, feedback_store
    body = request.get_json(silent=True) or {}
    api_key = body.get("api_key", "").strip()
    dataset_mode = str(body.get("dataset_mode", "new")).strip().lower()
    dataset_name = str(body.get("dataset_name", "")).strip()
    if not api_key:
        return jsonify({"error": "API key is required"}), 400

    use_mock = api_key.lower() in {"mock", "demo", "test"} or api_key.lower().startswith("mock_")
    source_mode = "mock"
    try:
        if use_mock:
            payload = get_mock_greenhouse_payload()
        else:
            payload = fetch_greenhouse_harvest_data(api_key)
            source_mode = "harvest"
    except urllib_error.HTTPError as exc:
        if exc.code in {401, 403}:
            return jsonify({"error": "Greenhouse rejected the API key or the key lacks the required Harvest permissions."}), 400
        return jsonify({"error": f"Greenhouse request failed with HTTP {exc.code}."}), 502
    except urllib_error.URLError as exc:
        return jsonify({"error": f"Could not reach Greenhouse Harvest API: {exc.reason}"}), 502
    except Exception as exc:
        return jsonify({"error": f"Greenhouse connection failed: {exc}"}), 500

    greenhouse_entries = normalize_greenhouse_payload(payload.get("scorecards", []), payload.get("candidates", []))
    ingest_result = ingest_grouped_entries(
        greenhouse_entries,
        dataset_mode=dataset_mode,
        dataset_name=dataset_name or "Greenhouse Import",
        source="greenhouse",
        split_mode="job" if dataset_mode != "merge" else "none",
    )

    greenhouse_state = {
        "connected": True,
        "last_sync": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "api_key": api_key[:8] + "..." if len(api_key) > 8 else api_key,
        "mode": source_mode,
    }
    greenhouse_api_key = None if source_mode == "mock" else api_key

    return jsonify({
        "status": "connected",
        "entries_loaded": ingest_result["entries_added"],
        "total": len(feedback_store),
        "mode": source_mode,
        "active_dataset_id": active_dataset_id,
        "datasets_created": len(ingest_result["datasets_created"]),
    })


@app.route("/api/greenhouse/sync", methods=["POST"])
def greenhouse_sync():
    """Sync latest data from Greenhouse or append a smaller mock sync payload."""
    global greenhouse_state, greenhouse_api_key
    if not greenhouse_state.get("connected"):
        return jsonify({"error": "Not connected to Greenhouse. Connect first."}), 400

    try:
        if greenhouse_state.get("mode") == "mock":
            payload = get_mock_greenhouse_sync_payload()
        else:
            if not greenhouse_api_key:
                return jsonify({"error": "Reconnect with the full Greenhouse key before syncing real Harvest data."}), 400
            payload = fetch_greenhouse_harvest_data(greenhouse_api_key)
    except urllib_error.HTTPError as exc:
        if exc.code in {401, 403}:
            return jsonify({"error": "Greenhouse rejected the API key or the key lacks the required Harvest permissions."}), 400
        return jsonify({"error": f"Greenhouse sync failed with HTTP {exc.code}."}), 502
    except urllib_error.URLError as exc:
        return jsonify({"error": f"Could not reach Greenhouse Harvest API: {exc.reason}"}), 502
    except Exception as exc:
        return jsonify({"error": f"Greenhouse sync failed: {exc}"}), 500

    new_entries = normalize_greenhouse_payload(payload.get("scorecards", []), payload.get("candidates", []))
    existing_source_ids = {
        (entry.get("source"), entry.get("source_id"))
        for entry in feedback_store
        if entry.get("source") and entry.get("source_id") is not None
    }
    new_entries = [
        entry for entry in new_entries
        if (entry.get("source"), entry.get("source_id")) not in existing_source_ids
    ]
    ingest_result = ingest_grouped_entries(
        new_entries,
        dataset_mode="merge",
        dataset_name="Greenhouse Sync",
        source="greenhouse",
        split_mode="none",
    )

    greenhouse_state["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return jsonify({
        "status": "synced",
        "new_entries": ingest_result["entries_added"],
        "total": len(feedback_store),
        "active_dataset_id": active_dataset_id,
    })


@app.route("/api/greenhouse/status")
def greenhouse_status():
    """Mock: Check Greenhouse connection status."""
    return jsonify(greenhouse_state)


@app.route("/api/llm/status")
def llm_status():
    """Return current LLM backend and availability of each option."""
    available = _check_backend_availability()
    return jsonify({
        "active": _active_llm_backend(),
        "ollama_model": llm_config.get("ollama_model", "qwen3.5:0.8b"),
        "available": available,
    })


@app.route("/api/llm/set", methods=["POST"])
def llm_set():
    """Switch the active LLM backend at runtime."""
    body = request.get_json(silent=True) or {}
    backend = str(body.get("backend", "")).strip().lower()
    if backend not in ("claude", "codex", "ollama"):
        return jsonify({"error": "Invalid backend"}), 400
    ollama_model = str(body.get("ollama_model", llm_config.get("ollama_model", "qwen3.5:0.8b"))).strip()
    llm_config["backend"] = backend
    llm_config["ollama_model"] = ollama_model
    return jsonify({"active": backend, "ollama_model": ollama_model})


@app.route("/api/datasets")
def list_datasets():
    return jsonify(build_dataset_summary())


@app.route("/api/datasets/select", methods=["POST"])
def select_dataset():
    body = request.get_json(silent=True) or {}
    dataset_id = str(body.get("dataset_id", "all")).strip() or "all"
    if not set_active_dataset(dataset_id):
        return jsonify({"error": "Dataset not found"}), 404
    return jsonify(build_dataset_summary())


@app.route("/api/datasets/<dataset_id>", methods=["DELETE"])
def delete_dataset(dataset_id):
    global feedback_store
    if dataset_id == "all":
        return jsonify({"error": "Cannot delete aggregate view"}), 400
    before = len(feedback_store)
    feedback_store = [entry for entry in feedback_store if entry.get("dataset_id") != dataset_id]
    if len(feedback_store) == before:
        return jsonify({"error": "Dataset not found"}), 404
    rebuild_dataset_registry()
    set_active_dataset("all")
    auto_save()
    return jsonify({"status": "deleted", "total": len(feedback_store)})


@app.route("/api/datasets/compare")
def compare_datasets():
    dataset_a = request.args.get("a", "").strip()
    dataset_b = request.args.get("b", "").strip()
    if not dataset_a or not dataset_b:
        return jsonify({"error": "Both dataset ids are required"}), 400
    entries_a = dataset_entries(dataset_a)
    entries_b = dataset_entries(dataset_b)
    if not entries_a or not entries_b:
        return jsonify({"error": "One or both datasets not found"}), 404
    analytics_a = compute_analytics(entries_a)
    analytics_b = compute_analytics(entries_b)
    return jsonify({
        "dataset_a": {
            "id": dataset_a,
            "summary": next((item for item in build_dataset_summary()["datasets"] if item["id"] == dataset_a), {"id": dataset_a}),
            "stats": analytics_a.get("stats", {}),
            "top_insights": analytics_a.get("top_insights", [])[:3],
            "top_role": (analytics_a.get("role_health") or [{}])[0],
            "top_interviewer": (analytics_a.get("interviewer_risk") or [{}])[0],
        },
        "dataset_b": {
            "id": dataset_b,
            "summary": next((item for item in build_dataset_summary()["datasets"] if item["id"] == dataset_b), {"id": dataset_b}),
            "stats": analytics_b.get("stats", {}),
            "top_insights": analytics_b.get("top_insights", [])[:3],
            "top_role": (analytics_b.get("role_health") or [{}])[0],
            "top_interviewer": (analytics_b.get("interviewer_risk") or [{}])[0],
        },
        "delta": {
            "pass_rate": round((analytics_a.get("stats", {}).get("overall_pass_rate", 0) - analytics_b.get("stats", {}).get("overall_pass_rate", 0)), 1),
            "consistency_score": round((analytics_a.get("stats", {}).get("consistency_score", 0) - analytics_b.get("stats", {}).get("consistency_score", 0)), 1),
            "review_queue": int(analytics_a.get("stats", {}).get("conflicted_candidates", 0) - analytics_b.get("stats", {}).get("conflicted_candidates", 0)),
        },
    })


if __name__ == "__main__":
    ensure_sessions_dir()
    feedback_store, data_source = load_initial_data()
    rebuild_dataset_registry()
    set_active_dataset("all")
    if feedback_store:
        if data_source == "session":
            print(f"Loaded {len(feedback_store)} feedback entries from the latest saved session")
        else:
            print(f"Loaded {len(feedback_store)} sample feedback entries")
    else:
        print("No sample data found — upload your own data via the Upload page")
    print("Starting HireSignal on http://localhost:8021")
    debug_mode = os.environ.get("FLASK_DEBUG") == "1"
    app.run(host="0.0.0.0", port=8021, debug=debug_mode, use_reloader=debug_mode)
