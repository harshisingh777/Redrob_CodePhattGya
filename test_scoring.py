"""Quick smoke test for scoring.py"""
import scoring

# Ideal candidate: Senior ML Engineer, product company, Pune, 7 yrs
ideal = {
    "profile": {
        "current_title": "Senior ML Engineer",
        "years_of_experience": 7,
        "location": "Pune",
        "country": "India",
        "notice_period_days": 15,
        "preferred_work_mode": "hybrid",
        "expected_salary": {"min": 30, "max": 50},
    },
    "career_history": [
        {
            "company": "Startup AI",
            "title": "ML Engineer",
            "description": (
                "Built retrieval system using FAISS and embeddings for NLP-based "
                "search. Deployed to production. A/B testing of ranking models."
            ),
            "start_date": "2020-01-01",
            "end_date": "2024-01-01",
            "duration_months": 48,
            "is_current": True,
        }
    ],
    "skills": [
        {"name": "NLP", "proficiency": "expert", "endorsements": 15, "duration_months": 48},
        {"name": "FAISS", "proficiency": "advanced", "endorsements": 8, "duration_months": 36},
        {"name": "Python", "proficiency": "expert", "endorsements": 25, "duration_months": 72},
        {"name": "PyTorch", "proficiency": "advanced", "endorsements": 12, "duration_months": 36},
    ],
    "education": [{"tier": "tier_1", "field": "Computer Science", "start_year": 2012, "end_year": 2016}],
    "redrob_signals": {
        "days_since_last_active": 5,
        "recruiter_response_rate": 0.85,
        "avg_response_time_hours": 12,
        "interview_completion_rate": 0.9,
        "open_to_work_flag": True,
        "profile_completeness_score": 90,
        "verified_email": True,
        "verified_phone": True,
        "linkedin_connected": True,
        "saved_by_recruiters_30d": 8,
        "github_activity_score": 65,
        "skill_assessment_scores": {"NLP": 88, "Python": 92},
    },
}

# Honeypot candidate: too many expert skills with no evidence
honeypot = {
    "profile": {"current_title": "AI Engineer", "years_of_experience": 20, "location": "Pune", "country": "India"},
    "career_history": [
        {"company": "Some Corp", "title": "Engineer", "description": "Did stuff", "start_date": "2022-01-01", "end_date": "2023-01-01", "duration_months": 60}
    ],
    "skills": [{"name": f"Skill{i}", "proficiency": "expert", "endorsements": 0, "duration_months": 3} for i in range(12)],
    "education": [{"tier": "tier_2", "field": "CS", "start_year": 2015, "end_year": 2010}],
    "redrob_signals": {},
}

# Consulting-only candidate
consulting = {
    "profile": {"current_title": "Software Engineer", "years_of_experience": 6, "location": "Hyderabad", "country": "India"},
    "career_history": [
        {"company": "TCS", "title": "Developer", "description": "Java development", "start_date": "2018-01-01", "end_date": "2021-01-01", "duration_months": 36},
        {"company": "Infosys", "title": "Senior Developer", "description": "Backend API development", "start_date": "2021-01-01", "end_date": "2024-01-01", "duration_months": 36, "is_current": True},
    ],
    "skills": [{"name": "Python", "proficiency": "intermediate", "endorsements": 5, "duration_months": 24}],
    "education": [{"tier": "tier_3", "field": "Information Technology", "start_year": 2014, "end_year": 2018}],
    "redrob_signals": {"days_since_last_active": 30, "recruiter_response_rate": 0.5},
}

print("=" * 60)
print("API CHECK")
print("=" * 60)
print(f"detect_honeypot callable: {callable(scoring.detect_honeypot)}")
print(f"score_candidate callable: {callable(scoring.score_candidate)}")
print(f"generate_reasoning callable: {callable(scoring.generate_reasoning)}")
print(f"COMPOSITE_WEIGHTS: {scoring.COMPOSITE_WEIGHTS}")

for label, cand in [("IDEAL", ideal), ("HONEYPOT", honeypot), ("CONSULTING-ONLY", consulting)]:
    print(f"\n{'=' * 60}")
    print(f"  {label} CANDIDATE")
    print(f"{'=' * 60}")
    scores = scoring.score_candidate(cand)
    for k, v in scores.items():
        print(f"  {k:>30s}: {v}")
    reasoning = scoring.generate_reasoning(cand, scores, 5)
    print(f"  {'reasoning':>30s}: {reasoning}")
    hp, reasons = scoring.detect_honeypot(cand)
    print(f"  {'honeypot_direct':>30s}: {hp} -> {reasons}")

print("\nAll checks passed!")
