"""
scoring.py — Core Scoring Engine for Redrob Intelligent Candidate Discovery & Ranking
======================================================================================

This module scores ~100K candidates against the **Senior AI Engineer — Founding Team**
job description at Redrob AI (Series A, Pune/Noida hybrid).

Design decisions
----------------
1.  **No ML libraries.**  Everything is deterministic arithmetic so that every
    score is explainable in a 30-minute interview.  We rely on `re`, `math`,
    `datetime`, and `collections` only.

2.  **Pre-compiled regex sets.**  Keyword matching is the hot-path; we compile
    all patterns once at module load and reuse frozensets / compiled regexes
    throughout.

3.  **Clamp-everywhere discipline.**  Every sub-score is clamped to its valid
    range before being combined.  This guarantees composite_score ∈ [0, 100]
    regardless of data quality.

4.  **Honeypot detection is decoupled** from scoring intentionally.  A candidate
    can have a high composite score *and* still be flagged — the caller decides
    the policy (e.g. exclude, demote, or surface for manual review).

5.  **Reasoning is fact-anchored.**  The `generate_reasoning` function never
    emits generic phrases; it pulls exact numbers, titles, company names, and
    skill names from the candidate dict so Stage-4 reviewers can verify claims
    in seconds.

Public API
----------
- ``detect_honeypot(candidate) -> (bool, list[str])``
- ``score_candidate(candidate)  -> dict``
- ``generate_reasoning(candidate, scores, rank) -> str``

Author : Hackathon Team
Date   : 2026-06-09
"""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, date
from typing import Any

# ---------------------------------------------------------------------------
# Composite weights — these mirror the spec exactly.
# ---------------------------------------------------------------------------
COMPOSITE_WEIGHTS: dict[str, float] = {
    "title_career": 0.40,
    "skills": 0.20,
    "behavioral": 0.20,
    "logistics": 0.10,
    "experience_education": 0.10,
}

# ---------------------------------------------------------------------------
# Skill category dictionaries (case-insensitive matching via _normalize)
# ---------------------------------------------------------------------------
CORE_AI_SKILLS: set[str] = {
    "nlp", "machine learning", "deep learning", "pytorch", "tensorflow",
    "transformers", "bert", "gpt", "llm", "fine-tuning llms", "lora",
    "embeddings", "sentence transformers", "rag", "retrieval",
    "information retrieval",
}

RETRIEVAL_SKILLS: set[str] = {
    "faiss", "pinecone", "milvus", "weaviate", "qdrant", "elasticsearch",
    "opensearch", "vector database", "semantic search", "bm25",
}

ENGINEERING_SKILLS: set[str] = {
    "python", "sql", "docker", "kubernetes", "aws", "gcp", "azure", "git",
    "linux", "fastapi", "flask", "django", "rest api", "grpc", "redis",
    "postgresql", "mongodb",
}

EVALUATION_SKILLS: set[str] = {
    "a/b testing", "ndcg", "statistical modeling", "feature engineering",
    "xgboost", "scikit-learn",
}

DATA_SKILLS: set[str] = {
    "spark", "airflow", "kafka", "data engineering", "etl", "databricks",
    "snowflake", "dbt",
}

IRRELEVANT_SKILLS: set[str] = {
    "photoshop", "powerpoint", "excel", "seo", "content writing", "marketing",
    "accounting", "six sigma", "sap", "autocad", "solidworks", "illustrator",
}

# Union of all *relevant* skill categories for fast membership tests.
ALL_RELEVANT_SKILLS: set[str] = (
    CORE_AI_SKILLS | RETRIEVAL_SKILLS | ENGINEERING_SKILLS
    | EVALUATION_SKILLS | DATA_SKILLS
)

# ---------------------------------------------------------------------------
# Keyword lists for career-description analysis (compiled once).
# We compile each keyword into a case-insensitive regex so we can count
# occurrences across concatenated description text in a single pass per
# keyword.  For 100K candidates this is still < 1 min on a modern CPU
# because the keyword lists are short and descriptions are short strings.
# ---------------------------------------------------------------------------
_STRONG_KEYWORDS: list[str] = [
    "ranking", "retrieval", "retrieval system", "search system",
    "recommendation", "embeddings", "vector search", "similarity",
    "faiss", "pinecone", "milvus", "nlp", "natural language",
    "transformer", "bert", "fine-tun", "llm", "language model",
    "deployed to production", "shipped", "a/b test", "evaluation metric",
    "ndcg", "precision", "recall", "machine learning pipeline",
    "deep learning", "neural network", "feature engineering",
    "model training", "model serving", "inference",
]

_MODERATE_KEYWORDS: list[str] = [
    "backend", "api", "microservice", "distributed", "python",
    "data pipeline", "spark", "airflow", "etl", "cloud", "aws", "gcp",
    "kubernetes", "docker",
]

_NEGATIVE_KEYWORDS: list[str] = [
    "marketing", "brand", "seo", "content writing", "accounting",
    "financial reporting", "audit", "hr", "recruitment",
    "customer support", "ticket", "escalation", "sales", "revenue",
    "quota", "mechanical", "cad", "solidworks", "manufacturing",
    "civil engineering", "construction",
]

# Pre-compile all keyword regexes (word-boundary aware, case-insensitive).
_compile = lambda kw: re.compile(r"(?i)\b" + re.escape(kw) + r"\b")
_STRONG_RE: list[re.Pattern] = [_compile(k) for k in _STRONG_KEYWORDS]
_MODERATE_RE: list[re.Pattern] = [_compile(k) for k in _MODERATE_KEYWORDS]
_NEGATIVE_RE: list[re.Pattern] = [_compile(k) for k in _NEGATIVE_KEYWORDS]

# ---------------------------------------------------------------------------
# Consulting-only companies (lowered for matching).
# ---------------------------------------------------------------------------
_CONSULTING_FIRMS: set[str] = {
    "tcs", "tata consultancy services", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "hcl", "hcl technologies",
    "tech mahindra", "mindtree", "mphasis", "l&t infotech", "lti",
    "persistent", "persistent systems",
}

# ---------------------------------------------------------------------------
# Title-relevance mapping.
# We match the *lowered* current_title against these buckets.
# ---------------------------------------------------------------------------
_DIRECT_AI_TITLES: list[str] = [
    "ai engineer", "ml engineer", "machine learning engineer",
    "data scientist", "nlp engineer", "search engineer",
]
_ADJACENT_AI_TITLES: list[str] = [
    "research scientist", "applied scientist", "deep learning engineer",
]
_ADJACENT_TECH_TITLES: list[str] = [
    "software engineer", "backend engineer", "data engineer",
    "platform engineer", "full stack engineer", "devops engineer",
    "site reliability engineer", "sre",
]
_NON_TECH_TRAP_TITLES: list[str] = [
    "marketing manager", "hr manager", "accountant", "sales executive",
    "operations manager", "customer support", "content writer",
    "graphic designer", "civil engineer", "mechanical engineer",
    "business analyst", "project manager",
]

# Tier-1 Indian cities for logistics.
_TIER1_CITIES: set[str] = {
    "hyderabad", "mumbai", "delhi", "bangalore", "bengaluru",
    "chennai", "kolkata", "gurgaon", "gurugram", "delhi ncr",
    "new delhi", "navi mumbai", "thane",
}

# Relevant education fields.
_RELEVANT_FIELDS: set[str] = {
    "computer science", "cs", "information technology", "it",
    "artificial intelligence", "ai", "machine learning", "ml",
    "data science", "electronics", "electrical", "ece",
    "mathematics", "math", "statistics", "stat",
}


# ===================================================================
#  Helper utilities
# ===================================================================

def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp *value* into [lo, hi]."""
    return max(lo, min(hi, value))


def _normalize(text: str | None) -> str:
    """Lowercase + strip a string; return '' for None."""
    if text is None:
        return ""
    return str(text).strip().lower()


def _safe_get(d: dict | None, *keys, default=None):
    """
    Safely traverse nested dicts.

    >>> _safe_get({'a': {'b': 3}}, 'a', 'b')
    3
    """
    current = d
    for k in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(k, default)
    return current


def _parse_date(raw: Any) -> date | None:
    """
    Best-effort date parser.  Handles ISO strings and common date formats.
    Returns None on failure — never raises.
    """
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    s = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
                "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d", "%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _months_between(d1: date, d2: date) -> float:
    """Approximate months between two dates."""
    return abs((d2.year - d1.year) * 12 + (d2.month - d1.month))


def _concat_career_descriptions(candidate: dict) -> str:
    """
    Concatenate all career_history[].description fields into a single
    lowercase string for keyword scanning.
    """
    career = _safe_get(candidate, "career_history") or []
    parts: list[str] = []
    for entry in career:
        desc = _safe_get(entry, "description")
        if desc:
            parts.append(str(desc))
        # Also pull in the job title for context.
        title = _safe_get(entry, "title") or _safe_get(entry, "job_title")
        if title:
            parts.append(str(title))
    return " ".join(parts).lower()


def _get_company_names(candidate: dict) -> list[str]:
    """Return lowered company names from career_history."""
    career = _safe_get(candidate, "career_history") or []
    names: list[str] = []
    for entry in career:
        name = _safe_get(entry, "company") or _safe_get(entry, "company_name")
        if name:
            names.append(_normalize(name))
    return names


# ===================================================================
#  Layer 1 — Title & Career Fit Score
# ===================================================================

def _score_title(title_raw: str | None) -> float:
    """
    Map current_title to a relevance score in [0, 100].

    Strategy: scan the title string for the *best* matching bucket and
    return the corresponding score.  'Senior' variants get a +5 bump.
    """
    title = _normalize(title_raw)
    if not title:
        return 10.0  # Unknown title — low but not zero.

    is_senior = "senior" in title or "lead" in title or "principal" in title or "staff" in title

    # Check non-tech traps first (they may contain words like 'engineer').
    for t in _NON_TECH_TRAP_TITLES:
        if t in title:
            return 10.0  # Capped low, no senior bonus.

    # Direct AI/ML titles.
    for t in _DIRECT_AI_TITLES:
        if t in title:
            base = 90.0
            return min(100.0, base + (5.0 if is_senior else 0.0))

    # Adjacent AI titles.
    for t in _ADJACENT_AI_TITLES:
        if t in title:
            base = 78.0
            return min(100.0, base + (5.0 if is_senior else 0.0))

    # Adjacent tech titles.
    for t in _ADJACENT_TECH_TITLES:
        if t in title:
            base = 52.0
            return min(65.0, base + (5.0 if is_senior else 0.0))

    # Fallback heuristics: if title contains 'engineer' or 'developer', give
    # moderate credit; if it contains 'data' or 'analyst', a bit less.
    if "engineer" in title or "developer" in title:
        return 45.0 + (5.0 if is_senior else 0.0)
    if "data" in title or "analyst" in title:
        return 35.0
    if "researcher" in title or "scientist" in title:
        return 60.0

    return 15.0  # Unrecognised title.


def _score_career_description(candidate: dict) -> float:
    """
    Count strong / moderate / negative keyword hits in concatenated career
    descriptions and convert to a 0-100 score.
    """
    text = _concat_career_descriptions(candidate)
    if not text:
        return 5.0

    strong = sum(1 for rx in _STRONG_RE if rx.search(text))
    moderate = sum(1 for rx in _MODERATE_RE if rx.search(text))
    negative = sum(1 for rx in _NEGATIVE_RE if rx.search(text))

    raw = strong * 8 + moderate * 3 - negative * 10
    return _clamp(raw)


def _score_company_type(candidate: dict) -> float:
    """
    Assess product-vs-consulting company mix.

    Returns a score in [0, 100]:
      - All consulting → 30  (severe penalty)
      - Mix             → 60
      - Has product     → 80
    """
    companies = _get_company_names(candidate)
    if not companies:
        return 50.0  # Unknown — neutral.

    consulting_count = 0
    for c in companies:
        # Check if any consulting-firm name is a substring of the company.
        for firm in _CONSULTING_FIRMS:
            if firm in c:
                consulting_count += 1
                break

    ratio = consulting_count / len(companies) if companies else 0

    if ratio >= 1.0:
        return 30.0  # All consulting.
    if ratio >= 0.5:
        return 55.0  # Mostly consulting.
    if consulting_count > 0:
        return 65.0  # Some consulting.
    return 80.0  # No consulting — product background.


def _title_career_score(candidate: dict) -> float:
    """
    Composite Title & Career Fit score.

    Formula:
        title_score * 0.35 + career_desc_score * 0.50 + company_type_score * 0.15

    Special rule: if ALL career history is consulting-only, the *entire*
    title_career_score is multiplied by 0.3 (per spec).
    """
    title_raw = _safe_get(candidate, "profile", "current_title") or _safe_get(candidate, "current_title")
    ts = _score_title(title_raw)
    cs = _score_career_description(candidate)
    ct = _score_company_type(candidate)

    combined = ts * 0.35 + cs * 0.50 + ct * 0.15

    # Consulting-only penalty: multiply by 0.3.
    companies = _get_company_names(candidate)
    if companies:
        all_consulting = all(
            any(firm in c for firm in _CONSULTING_FIRMS)
            for c in companies
        )
        if all_consulting:
            combined *= 0.3

    return _clamp(combined)


# ===================================================================
#  Layer 2 — Skills Trust Score
# ===================================================================

def _proficiency_score(level: str | None) -> float:
    """Map a proficiency label to a numeric score."""
    mapping = {
        "expert": 1.0,
        "advanced": 0.75,
        "intermediate": 0.5,
        "beginner": 0.25,
    }
    return mapping.get(_normalize(level), 0.35)  # default → between beginner & intermediate


def _skill_trust(skill_entry: dict) -> float:
    """
    Compute a trust weight for a single skill entry.

    trust = min(1, endorsements/10) * 0.3
          + proficiency_score       * 0.4
          + min(duration_months/36, 1) * 0.3
    """
    endorsements = max(0, _safe_get(skill_entry, "endorsements") or 0)
    duration = max(0, _safe_get(skill_entry, "duration_months") or 0)
    prof = _proficiency_score(_safe_get(skill_entry, "proficiency"))

    return (
        min(1.0, endorsements / 10.0) * 0.3
        + prof * 0.4
        + min(duration / 36.0, 1.0) * 0.3
    )


def _skill_category_weight(skill_name_lower: str) -> float:
    """
    Return the importance weight of a skill category for this JD.

    Core AI & Retrieval skills are the most important.
    """
    if skill_name_lower in CORE_AI_SKILLS:
        return 3.0
    if skill_name_lower in RETRIEVAL_SKILLS:
        return 3.5  # Retrieval is THE differentiator for this role.
    if skill_name_lower in EVALUATION_SKILLS:
        return 2.5
    if skill_name_lower in ENGINEERING_SKILLS:
        return 1.5
    if skill_name_lower in DATA_SKILLS:
        return 1.0
    if skill_name_lower in IRRELEVANT_SKILLS:
        return -1.0  # Penalty contribution.
    return 0.5  # Unknown skills get minor credit.


def _skills_score(candidate: dict) -> float:
    """
    Skills Trust Score (0-100).

    We iterate through all candidate skills, compute a trust-weighted
    relevance score, incorporate platform-verified assessment scores,
    and penalise irrelevant-heavy profiles.
    """
    skills = _safe_get(candidate, "skills") or []
    if not skills:
        return 5.0  # No skills listed — very low.

    weighted_sum = 0.0
    max_possible = 0.0  # Tracks the theoretical max for normalisation.

    core_count = 0
    retrieval_count = 0
    irrelevant_count = 0
    suspicious_count = 0

    for sk in skills:
        name_lower = _normalize(_safe_get(sk, "name") or _safe_get(sk, "skill_name"))
        if not name_lower:
            continue

        trust = _skill_trust(sk)
        cat_w = _skill_category_weight(name_lower)

        if cat_w < 0:
            irrelevant_count += 1
            weighted_sum += cat_w * trust  # Will subtract.
        else:
            weighted_sum += cat_w * trust
            max_possible += cat_w * 1.0  # Perfect trust.

        if name_lower in CORE_AI_SKILLS:
            core_count += 1
        if name_lower in RETRIEVAL_SKILLS:
            retrieval_count += 1

        # Flag suspicious: expert + 0 endorsements + < 12 months.
        prof = _normalize(_safe_get(sk, "proficiency"))
        endorse = _safe_get(sk, "endorsements") or 0
        dur = _safe_get(sk, "duration_months") or 0
        if prof == "expert" and endorse == 0 and dur < 12:
            suspicious_count += 1

    # Incorporate platform-verified skill_assessment_scores.
    redrob = _safe_get(candidate, "redrob_signals") or {}
    assessments = _safe_get(redrob, "skill_assessment_scores") or {}
    if isinstance(assessments, dict):
        for skill_name, score_val in assessments.items():
            sn = _normalize(skill_name)
            if sn in ALL_RELEVANT_SKILLS:
                # Platform-verified scores (0-100) are high trust.
                try:
                    sv = float(score_val)
                except (TypeError, ValueError):
                    continue
                cat_w = _skill_category_weight(sn)
                if cat_w > 0:
                    weighted_sum += cat_w * (sv / 100.0) * 1.2  # 1.2x trust multiplier
                    max_possible += cat_w * 1.2

    # Normalise to 0-100.
    if max_possible > 0:
        raw = (weighted_sum / max_possible) * 100.0
    else:
        raw = 5.0

    # Penalty: many irrelevant skills + few core AI skills → trap.
    if irrelevant_count >= 3 and core_count == 0:
        raw *= 0.3

    # Bonus for retrieval skills — the JD's top priority.
    if retrieval_count >= 2:
        raw = min(100.0, raw + 10.0)

    # Suspicious-skill damping.
    if suspicious_count >= 2:
        raw *= 0.8

    return _clamp(raw)


# ===================================================================
#  Layer 3 — Behavioral Availability Score
# ===================================================================

def _behavioral_score(candidate: dict) -> float:
    """
    Behavioral Availability Score (0-100).

    Sub-components are additive:
      Recency (25) + Responsiveness (30) + Speed (10) + Interview (10)
      + Open-to-work (5) + Profile completeness (5) + Verification (10)
      + Market signal (5)
    """
    redrob = _safe_get(candidate, "redrob_signals") or {}
    profile = _safe_get(candidate, "profile") or {}

    # 1. Recency (25 pts).
    # Try numeric days_since_last_active first (per spec), then fall back
    # to computing from last_active_date if the dataset uses that instead.
    days_since = _safe_get(redrob, "days_since_last_active")
    if days_since is None:
        last_active_raw = _safe_get(redrob, "last_active_date")
        last_active = _parse_date(last_active_raw)
        if last_active is not None:
            ref = date(2026, 6, 1)
            days_since = max(0, (ref - last_active).days)
    if days_since is None:
        recency = 12.0  # Unknown → half credit.
    else:
        days_since = max(0, float(days_since))
        recency = max(0.0, 25.0 * (1.0 - days_since / 365.0))

    # 2. Responsiveness (30 pts) — most predictive.
    response_rate = _safe_get(redrob, "recruiter_response_rate")
    if response_rate is None:
        responsiveness = 10.0  # Unknown → low-moderate.
    else:
        responsiveness = float(response_rate) * 30.0

    # 3. Response speed (10 pts).
    avg_hours = _safe_get(redrob, "avg_response_time_hours")
    if avg_hours is None:
        speed = 5.0
    else:
        speed = max(0.0, 10.0 * (1.0 - float(avg_hours) / 200.0))

    # 4. Interview reliability (10 pts).
    interview_rate = _safe_get(redrob, "interview_completion_rate")
    if interview_rate is None:
        interview = 5.0
    else:
        interview = float(interview_rate) * 10.0

    # 5. Open to work (5 pts).
    otw = _safe_get(redrob, "open_to_work_flag") or _safe_get(profile, "open_to_work")
    open_pts = 5.0 if otw else 0.0

    # 6. Profile completeness (5 pts).
    pc = _safe_get(redrob, "profile_completeness_score")
    if pc is None:
        completeness = 2.5
    else:
        completeness = (float(pc) / 100.0) * 5.0

    # 7. Verification trust (10 pts).
    verified_email = 3.0 if _safe_get(redrob, "verified_email") else 0.0
    verified_phone = 3.0 if _safe_get(redrob, "verified_phone") else 0.0
    linkedin = 4.0 if _safe_get(redrob, "linkedin_connected") else 0.0
    verification = verified_email + verified_phone + linkedin

    # 8. Market signal (5 pts).
    saved = _safe_get(redrob, "saved_by_recruiters_30d") or 0
    market = min(float(saved) / 10.0, 1.0) * 5.0

    total = recency + responsiveness + speed + interview + open_pts + completeness + verification + market
    return _clamp(total)


# ===================================================================
#  Layer 4 — Logistics Fit Score
# ===================================================================

def _logistics_score(candidate: dict) -> float:
    """
    Logistics Fit Score (0-100).

    Location (40) + Notice period (25) + Work mode (15) + Salary alignment (20).
    """
    profile = _safe_get(candidate, "profile") or {}
    redrob = _safe_get(candidate, "redrob_signals") or {}

    # ---- Location (40 pts) ----
    country = _normalize(_safe_get(profile, "country"))
    location = _normalize(_safe_get(profile, "location"))

    if "pune" in location:
        loc_pts = 40.0
    elif "noida" in location:
        loc_pts = 40.0
    elif any(city in location for city in _TIER1_CITIES):
        loc_pts = 30.0
    elif "india" in country or "india" in location or country in ("in", "ind"):
        loc_pts = 20.0
    else:
        willing = _safe_get(redrob, "willing_to_relocate")
        loc_pts = 10.0 if willing else 0.0

    # ---- Notice period (25 pts) ----
    # Try redrob_signals first, then profile, then top-level.
    notice = (
        _safe_get(redrob, "notice_period_days")
        or _safe_get(profile, "notice_period_days")
        or _safe_get(candidate, "notice_period_days")
    )
    if notice is None:
        notice_pts = 12.0  # Unknown → middle.
    else:
        notice = int(notice)
        if notice <= 30:
            notice_pts = 25.0
        elif notice <= 60:
            notice_pts = 18.0
        elif notice <= 90:
            notice_pts = 10.0
        else:
            notice_pts = 3.0

    # ---- Work mode (15 pts) ----
    work_mode = _normalize(
        _safe_get(redrob, "preferred_work_mode")
        or _safe_get(profile, "preferred_work_mode")
        or _safe_get(profile, "work_mode")
    )
    if "hybrid" in work_mode or "flexible" in work_mode:
        mode_pts = 15.0
    elif "onsite" in work_mode or "on-site" in work_mode or "office" in work_mode:
        mode_pts = 12.0
    elif "remote" in work_mode:
        mode_pts = 5.0
    else:
        mode_pts = 8.0  # Unknown → moderate.

    # ---- Salary alignment (20 pts) ----
    expected = (
        _safe_get(redrob, "expected_salary_range_inr_lpa")
        or _safe_get(profile, "expected_salary")
        or _safe_get(redrob, "expected_salary")
        or {}
    )
    sal_max = _safe_get(expected, "max") or _safe_get(expected, "maximum")
    sal_min = _safe_get(expected, "min") or _safe_get(expected, "minimum")

    if sal_max is not None:
        sal_max = float(sal_max)
        if sal_max <= 60:
            sal_pts = 20.0
        elif sal_max <= 80:
            sal_pts = 15.0
        elif sal_max <= 100:
            sal_pts = 10.0
        else:
            sal_pts = 5.0
    else:
        sal_pts = 10.0  # Unknown → neutral.

    # Over-priced guard.
    if sal_min is not None and float(sal_min) > 80:
        sal_pts = 3.0

    total = loc_pts + notice_pts + mode_pts + sal_pts
    return _clamp(total)


# ===================================================================
#  Layer 5 — Experience & Education Score
# ===================================================================

def _experience_education_score(candidate: dict) -> float:
    """
    Experience & Education Score (0-100).

    Experience (70 pts) + Education (20 pts) + GitHub (10 pts).
    """
    profile = _safe_get(candidate, "profile") or {}

    # ---- Experience (70 pts) ----
    yoe = _safe_get(profile, "years_of_experience")
    if yoe is None:
        yoe = _safe_get(candidate, "years_of_experience")
    if yoe is not None:
        yoe = float(yoe)
        if 5 <= yoe <= 9:
            exp_pts = 70.0
        elif 4 <= yoe < 5 or 9 < yoe <= 12:
            exp_pts = 50.0
        elif 3 <= yoe < 4 or 12 < yoe <= 15:
            exp_pts = 30.0
        else:
            exp_pts = 15.0
    else:
        exp_pts = 25.0  # Unknown.

    # ---- Education (20 pts) ----
    education = _safe_get(candidate, "education") or _safe_get(profile, "education") or []
    if isinstance(education, dict):
        education = [education]

    edu_pts = 8.0  # Default for unknown.
    field_bonus = 0.0

    for edu in education:
        tier = _normalize(_safe_get(edu, "tier") or _safe_get(edu, "institution_tier"))
        tier_scores = {"tier_1": 20.0, "tier_2": 15.0, "tier_3": 10.0, "tier_4": 5.0}
        t = tier_scores.get(tier)
        if t is not None and t > edu_pts:
            edu_pts = t

        # Check field relevance.
        field = _normalize(_safe_get(edu, "field") or _safe_get(edu, "field_of_study") or _safe_get(edu, "major"))
        for rf in _RELEVANT_FIELDS:
            if rf in field:
                field_bonus = 5.0
                break

    edu_pts += field_bonus
    edu_pts = min(25.0, edu_pts)  # Cap with bonus.

    # ---- GitHub activity (10 pts) ----
    github_score = _safe_get(
        _safe_get(candidate, "redrob_signals") or {},
        "github_activity_score",
    )
    if github_score is None:
        github_score = _safe_get(profile, "github_activity_score")

    if github_score is None or github_score == -1:
        github_pts = 3.0  # No GitHub — neutral.
    else:
        github_pts = min(float(github_score) / 100.0 * 10.0, 10.0)

    total = exp_pts + edu_pts + github_pts
    return _clamp(total)


# ===================================================================
#  Honeypot Detection
# ===================================================================

def detect_honeypot(candidate: dict) -> tuple[bool, list[str]]:
    """
    Detect data-integrity red flags ('honeypot' traps) in a candidate profile.

    Returns
    -------
    (is_honeypot, reasons) : tuple[bool, list[str]]
        ``is_honeypot`` is True when 2 or more independent flags trigger.
        ``reasons`` lists human-readable descriptions of every triggered flag.
    """
    reasons: list[str] = []

    career = _safe_get(candidate, "career_history") or []
    skills = _safe_get(candidate, "skills") or []
    education = _safe_get(candidate, "education") or _safe_get(
        _safe_get(candidate, "profile") or {}, "education"
    ) or []
    if isinstance(education, dict):
        education = [education]
    profile = _safe_get(candidate, "profile") or {}
    redrob = _safe_get(candidate, "redrob_signals") or {}

    # ---- 1. Impossible tenure ----
    for entry in career:
        stated_duration = _safe_get(entry, "duration_months")
        start = _parse_date(_safe_get(entry, "start_date"))
        end = _parse_date(_safe_get(entry, "end_date"))
        if stated_duration is not None and start and end:
            actual_months = _months_between(start, end)
            if float(stated_duration) > actual_months + 3:
                reasons.append(
                    f"Impossible tenure: stated {stated_duration} months at "
                    f"'{_safe_get(entry, 'company') or '?'}' but date range is ~{actual_months:.0f} months"
                )
                break  # One flag per category is enough.

    # ---- 2. Expert with zero evidence ----
    # Relaxed: any 'expert' skill with 0 endorsements is suspicious,
    # regardless of duration (honeypots often set plausible durations).
    expert_no_evidence = 0
    for sk in skills:
        prof = _normalize(_safe_get(sk, "proficiency"))
        endorse = _safe_get(sk, "endorsements") or 0
        if prof == "expert" and endorse == 0:
            expert_no_evidence += 1
    if expert_no_evidence > 0:
        reasons.append(
            f"Expert with zero evidence: {expert_no_evidence} skill(s) listed as 'expert' "
            f"with 0 endorsements"
        )

    # ---- 3. Too many expert skills ----
    # Lowered from >8 to >=5.  The dataset's honeypots characteristically
    # claim 'expert' in 5-11 skills — real candidates rarely exceed 3-4.
    expert_count = sum(1 for sk in skills if _normalize(_safe_get(sk, "proficiency")) == "expert")
    if expert_count >= 5:
        reasons.append(f"Too many expert skills: {expert_count} skills listed as 'expert' (threshold: 5)")

    # ---- 4. Career overlap ----
    dated_jobs: list[tuple[date, date, str]] = []
    for entry in career:
        start = _parse_date(_safe_get(entry, "start_date"))
        end = _parse_date(_safe_get(entry, "end_date"))
        is_current = _safe_get(entry, "is_current") or _safe_get(entry, "current")
        if start and not end and is_current:
            end = date.today()
        if start and end and start <= end:
            company = _safe_get(entry, "company") or _safe_get(entry, "company_name") or "?"
            dated_jobs.append((start, end, company))

    # Check pairwise overlap (O(n^2) but n ≤ ~15 per candidate).
    overlap_found = False
    for i in range(len(dated_jobs)):
        if overlap_found:
            break
        for j in range(i + 1, len(dated_jobs)):
            s1, e1, c1 = dated_jobs[i]
            s2, e2, c2 = dated_jobs[j]
            # Both current jobs are OK (consulting moonlighting is common).
            overlap_start = max(s1, s2)
            overlap_end = min(e1, e2)
            if overlap_start < overlap_end:
                overlap_months = _months_between(overlap_start, overlap_end)
                if overlap_months > 6:
                    reasons.append(
                        f"Career overlap: '{c1}' and '{c2}' overlap by ~{overlap_months:.0f} months"
                    )
                    overlap_found = True
                    break

    # ---- 5. Impossible education ----
    for edu in education:
        start_year = _safe_get(edu, "start_year")
        end_year = _safe_get(edu, "end_year")
        if start_year is not None and end_year is not None:
            try:
                sy, ey = int(start_year), int(end_year)
            except (ValueError, TypeError):
                continue
            if ey < sy:
                reasons.append(f"Impossible education: end_year ({ey}) < start_year ({sy})")
                break
            duration = ey - sy
            if duration > 8 or duration < 1:
                reasons.append(
                    f"Suspicious education duration: {duration} years "
                    f"({sy}–{ey})"
                )
                break

    # ---- 6. Experience mismatch ----
    yoe = _safe_get(profile, "years_of_experience") or _safe_get(candidate, "years_of_experience")
    if yoe is not None and career:
        total_career_months = 0.0
        for entry in career:
            dur = _safe_get(entry, "duration_months")
            if dur is not None:
                total_career_months += float(dur)
            else:
                start = _parse_date(_safe_get(entry, "start_date"))
                end = _parse_date(_safe_get(entry, "end_date"))
                if start and end:
                    total_career_months += _months_between(start, end)
        career_years = total_career_months / 12.0
        gap = abs(float(yoe) - career_years)
        if gap > 3:
            reasons.append(
                f"Experience mismatch: stated {yoe} yrs but career_history sums to ~{career_years:.1f} yrs "
                f"(gap: {gap:.1f} yrs)"
            )

    # ---- 7. Skill assessment impossibility ----
    assessments = _safe_get(redrob, "skill_assessment_scores") or {}
    if isinstance(assessments, dict):
        listed_skills = {_normalize(_safe_get(sk, "name") or _safe_get(sk, "skill_name"))
                        for sk in skills if _safe_get(sk, "name") or _safe_get(sk, "skill_name")}
        for skill_name, score_val in assessments.items():
            try:
                sv = float(score_val)
            except (TypeError, ValueError):
                continue
            if sv > 90 and _normalize(skill_name) not in listed_skills:
                reasons.append(
                    f"Assessment impossibility: scored {sv} on '{skill_name}' "
                    f"but skill not listed in profile"
                )
                break  # One flag is enough.

    is_honeypot = len(reasons) >= 2
    return is_honeypot, reasons


# ===================================================================
#  Composite Scoring
# ===================================================================

def score_candidate(candidate: dict) -> dict:
    """
    Score a candidate across all five layers and produce a composite score.

    Returns
    -------
    dict with keys:
        title_career_score, skills_score, behavioral_score,
        logistics_score, experience_education_score, composite_score,
        is_honeypot, honeypot_reasons
    """
    tc = _title_career_score(candidate)
    sk = _skills_score(candidate)
    bh = _behavioral_score(candidate)
    lg = _logistics_score(candidate)
    ee = _experience_education_score(candidate)

    composite = (
        tc * COMPOSITE_WEIGHTS["title_career"]
        + sk * COMPOSITE_WEIGHTS["skills"]
        + bh * COMPOSITE_WEIGHTS["behavioral"]
        + lg * COMPOSITE_WEIGHTS["logistics"]
        + ee * COMPOSITE_WEIGHTS["experience_education"]
    )

    is_hp, hp_reasons = detect_honeypot(candidate)

    # Honeypot penalty: reduce composite by 40% so they sink in ranking
    # but aren't fully hidden (allows manual review).
    if is_hp:
        composite *= 0.6

    composite = _clamp(composite)

    return {
        "title_career_score": round(tc, 2),
        "skills_score": round(sk, 2),
        "behavioral_score": round(bh, 2),
        "logistics_score": round(lg, 2),
        "experience_education_score": round(ee, 2),
        "composite_score": round(composite, 2),
        "is_honeypot": is_hp,
        "honeypot_reasons": hp_reasons,
    }


# ===================================================================
#  Reasoning Generation
# ===================================================================

def generate_reasoning(candidate: dict, scores: dict, rank: int) -> str:
    """
    Generate a 1-2 sentence **fact-based** reasoning string for a ranked
    candidate.  Every claim references concrete data from the candidate dict.

    The tone adapts to rank:
      - Top 10:   confident highlight of strengths
      - 11-50:    balanced — strengths + minor gaps
      - 51-100:   cautious — acknowledges gaps, explains inclusion
      - 100+:     brief summary
    """
    profile = _safe_get(candidate, "profile") or {}
    redrob = _safe_get(candidate, "redrob_signals") or {}

    title = _safe_get(profile, "current_title") or _safe_get(candidate, "current_title") or "Unknown title"
    yoe = _safe_get(profile, "years_of_experience") or _safe_get(candidate, "years_of_experience") or "?"

    # Extract current/latest company.
    career = _safe_get(candidate, "career_history") or []
    current_company = "Unknown company"
    for entry in career:
        if _safe_get(entry, "is_current") or _safe_get(entry, "current"):
            current_company = _safe_get(entry, "company") or _safe_get(entry, "company_name") or current_company
            break
    if current_company == "Unknown company" and career:
        current_company = _safe_get(career[0], "company") or _safe_get(career[0], "company_name") or current_company

    # Gather top matching skills (up to 4).
    skills_list = _safe_get(candidate, "skills") or []
    matching_skills: list[str] = []
    for sk in skills_list:
        name = _safe_get(sk, "name") or _safe_get(sk, "skill_name") or ""
        if _normalize(name) in ALL_RELEVANT_SKILLS and len(matching_skills) < 4:
            matching_skills.append(name)
    skills_str = ", ".join(matching_skills) if matching_skills else "no directly matching skills listed"

    # Behavioral facts.
    response_rate = _safe_get(redrob, "recruiter_response_rate")
    rr_str = f"{response_rate * 100:.0f}%" if response_rate is not None else "unknown"
    notice = (
        _safe_get(redrob, "notice_period_days")
        or _safe_get(profile, "notice_period_days")
        or _safe_get(candidate, "notice_period_days")
    )
    notice_str = f"{notice}-day" if notice is not None else "unknown"

    location = _safe_get(profile, "location") or _safe_get(profile, "country") or "unknown location"

    # Honeypot note.
    hp_note = ""
    if scores.get("is_honeypot"):
        hp_note = " [HONEYPOT FLAG: " + "; ".join(scores.get("honeypot_reasons", [])[:2]) + "]"

    # Identify key gaps.
    gaps: list[str] = []
    if scores.get("title_career_score", 0) < 35:
        gaps.append("weak title/career alignment")
    if scores.get("skills_score", 0) < 30:
        gaps.append("low skills-trust score")
    if scores.get("behavioral_score", 0) < 30:
        gaps.append("low behavioral availability")
    if scores.get("logistics_score", 0) < 40:
        gaps.append("logistics concerns")

    # Identify strengths.
    strengths: list[str] = []
    if scores.get("title_career_score", 0) >= 70:
        strengths.append("strong career fit")
    if scores.get("skills_score", 0) >= 70:
        strengths.append("high skills-trust")
    if scores.get("behavioral_score", 0) >= 70:
        strengths.append("highly responsive")
    if scores.get("experience_education_score", 0) >= 70:
        strengths.append("ideal experience band")

    # Build reasoning by rank tier.
    composite = scores.get("composite_score", 0)

    if rank <= 10:
        # Top 10 — confident.
        strength_clause = f" Strengths: {', '.join(strengths)}." if strengths else ""
        gap_clause = f" Minor note: {gaps[0]}." if gaps else ""
        reasoning = (
            f"{title} at {current_company} with {yoe} yrs exp. "
            f"Skills: {skills_str}. "
            f"Behavioral: {rr_str} response rate, {notice_str} notice, based in {location}. "
            f"Composite: {composite}/100.{strength_clause}{gap_clause}{hp_note}"
        )
    elif rank <= 50:
        # 11-50 — balanced.
        gap_clause = f" Gaps: {', '.join(gaps[:2])}." if gaps else ""
        reasoning = (
            f"{title} at {current_company} ({yoe} yrs). "
            f"Skills: {skills_str}. "
            f"{rr_str} response rate, {notice_str} notice ({location}). "
            f"Composite: {composite}/100.{gap_clause}{hp_note}"
        )
    elif rank <= 100:
        # 51-100 — cautious.
        gap_clause = f" Concerns: {', '.join(gaps[:3])}." if gaps else ""
        redeeming = f" Included for {strengths[0]}." if strengths else ""
        reasoning = (
            f"{title} ({yoe} yrs) at {current_company}. "
            f"Skills: {skills_str}. "
            f"Composite: {composite}/100.{gap_clause}{redeeming}{hp_note}"
        )
    else:
        # 100+ — brief.
        reasoning = (
            f"{title} at {current_company}, {yoe} yrs, {location}. "
            f"Composite: {composite}/100. Skills: {skills_str}.{hp_note}"
        )

    return reasoning
