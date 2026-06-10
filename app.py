import streamlit as st
import json
import io
import csv
import scoring

# ---------------------------------------------------------------------------
# Built-in sample profiles
# ---------------------------------------------------------------------------
SAMPLE_1 = {
  "candidate_id": "CAND_IDEAL_01",
  "profile": {
    "anonymized_name": "Aarav Sharma",
    "headline": "Senior ML Engineer | Search & Retrieval | RAG & Vector DBs",
    "summary": "Senior Machine Learning Engineer with 7 years specializing in search, recommendation, and LLMs. Shipped FAISS/Milvus retrieval systems to production.",
    "location": "Pune", "country": "India",
    "years_of_experience": 7.0,
    "current_title": "Senior Machine Learning Engineer",
    "current_company": "InnoTech",
    "current_company_size": "201-500",
    "current_industry": "Software Products"
  },
  "career_history": [
    {"company": "InnoTech", "title": "Senior Machine Learning Engineer",
     "start_date": "2023-01-10", "end_date": None, "duration_months": 41,
     "is_current": True, "industry": "Software Products", "company_size": "201-500",
     "description": "Led hybrid search engine with Milvus; improved NDCG@10 by 14%. Designed MRR/NDCG evaluation frameworks."},
    {"company": "DataFlow Labs", "title": "ML Engineer",
     "start_date": "2019-06-01", "end_date": "2022-12-31", "duration_months": 43,
     "is_current": False, "industry": "Software Products", "company_size": "51-200",
     "description": "Fine-tuned BERT models; set up Pinecone semantic search."}
  ],
  "education": [{"institution": "IIT Bombay", "degree": "B.Tech.", "field_of_study": "CS",
                  "start_year": 2015, "end_year": 2019, "grade": "8.8", "tier": "tier_1"}],
  "skills": [
    {"name": "Python", "proficiency": "expert", "endorsements": 85, "duration_months": 80},
    {"name": "Milvus", "proficiency": "expert", "endorsements": 42, "duration_months": 36},
    {"name": "Vector Databases", "proficiency": "expert", "endorsements": 30, "duration_months": 36},
    {"name": "PyTorch", "proficiency": "expert", "endorsements": 55, "duration_months": 48},
    {"name": "NDCG", "proficiency": "advanced", "endorsements": 15, "duration_months": 24}
  ],
  "redrob_signals": {
    "profile_completeness_score": 95.0, "signup_date": "2024-01-01",
    "last_active_date": "2026-06-05", "open_to_work_flag": True,
    "profile_views_received_30d": 45, "applications_submitted_30d": 1,
    "recruiter_response_rate": 0.85, "avg_response_time_hours": 12.0,
    "skill_assessment_scores": {"Python": 88.0, "Milvus": 82.0},
    "connection_count": 520, "endorsements_received": 180,
    "notice_period_days": 15,
    "expected_salary_range_inr_lpa": {"min": 35.0, "max": 50.0},
    "preferred_work_mode": "hybrid", "willing_to_relocate": True,
    "github_activity_score": 75.0, "search_appearance_30d": 350,
    "saved_by_recruiters_30d": 15, "interview_completion_rate": 0.90,
    "offer_acceptance_rate": 0.75, "verified_email": True,
    "verified_phone": True, "linkedin_connected": True
  }
}

SAMPLE_2 = {
  "candidate_id": "CAND_STUFFER_02",
  "profile": {
    "anonymized_name": "Saanvi Sethi",
    "headline": "Operations Manager | Expert in PyTorch, Milvus, LLMs",
    "summary": "Experienced Operations Manager. Recently completed tutorials in AI/ML.",
    "location": "Chennai", "country": "India",
    "years_of_experience": 12.5,
    "current_title": "Operations Manager",
    "current_company": "Wipro", "current_company_size": "10001+",
    "current_industry": "IT Services"
  },
  "career_history": [
    {"company": "Wipro", "title": "Operations Manager",
     "start_date": "2022-11-14", "end_date": None, "duration_months": 43,
     "is_current": True, "industry": "IT Services", "company_size": "10001+",
     "description": "Managed customer support operations. Lighter on technical depth."}
  ],
  "education": [{"institution": "Lovely Professional University", "degree": "B.B.A.",
                  "field_of_study": "Business", "start_year": 2010, "end_year": 2013,
                  "grade": "7.5", "tier": "tier_3"}],
  "skills": [
    {"name": "Python", "proficiency": "expert", "endorsements": 0, "duration_months": 2},
    {"name": "Milvus", "proficiency": "expert", "endorsements": 0, "duration_months": 1},
    {"name": "PyTorch", "proficiency": "expert", "endorsements": 0, "duration_months": 1},
    {"name": "Fine-tuning LLMs", "proficiency": "expert", "endorsements": 0, "duration_months": 1}
  ],
  "redrob_signals": {
    "profile_completeness_score": 70.0, "signup_date": "2025-05-01",
    "last_active_date": "2026-05-15", "open_to_work_flag": True,
    "profile_views_received_30d": 5, "applications_submitted_30d": 12,
    "recruiter_response_rate": 0.20, "avg_response_time_hours": 150.0,
    "skill_assessment_scores": {}, "connection_count": 120,
    "endorsements_received": 5, "notice_period_days": 90,
    "expected_salary_range_inr_lpa": {"min": 15.0, "max": 25.0},
    "preferred_work_mode": "onsite", "willing_to_relocate": False,
    "github_activity_score": 2.0, "search_appearance_30d": 20,
    "saved_by_recruiters_30d": 1, "interview_completion_rate": 0.40,
    "offer_acceptance_rate": 0.50, "verified_email": True,
    "verified_phone": True, "linkedin_connected": False
  }
}

SAMPLE_3 = {
  "candidate_id": "CAND_HONEYPOT_03",
  "profile": {
    "anonymized_name": "Suspicious Dev",
    "headline": "AI Guru | Milvus, FAISS, PyTorch Expert",
    "summary": "AI Engineer with 5 years experience.",
    "location": "Noida", "country": "India",
    "years_of_experience": 5.0,
    "current_title": "AI Lead",
    "current_company": "Startup X", "current_company_size": "11-50",
    "current_industry": "Software Products"
  },
  "career_history": [
    {"company": "Startup X", "title": "AI Lead",
     "start_date": "2025-01-01", "end_date": "2025-10-31",
     "duration_months": 60,   # 60 months claimed for a 10-month job = honeypot
     "is_current": False, "industry": "Software Products",
     "description": "Built AI retrieval systems."}
  ],
  "education": [{"institution": "Amity University", "degree": "B.Tech.",
                  "field_of_study": "CS", "start_year": 2016, "end_year": 2020,
                  "grade": "8.0", "tier": "tier_3"}],
  "skills": [
    {"name": "Python",     "proficiency": "expert", "endorsements": 0, "duration_months": 1},
    {"name": "PyTorch",    "proficiency": "expert", "endorsements": 0, "duration_months": 2},
    {"name": "Milvus",     "proficiency": "expert", "endorsements": 0, "duration_months": 1},
    {"name": "FAISS",      "proficiency": "expert", "endorsements": 0, "duration_months": 1},
    {"name": "NLP",        "proficiency": "expert", "endorsements": 0, "duration_months": 1},
    {"name": "Embeddings", "proficiency": "expert", "endorsements": 0, "duration_months": 1}
  ],
  "redrob_signals": {
    "profile_completeness_score": 80.0, "signup_date": "2025-11-01",
    "last_active_date": "2026-05-30", "open_to_work_flag": True,
    "profile_views_received_30d": 12, "applications_submitted_30d": 4,
    "recruiter_response_rate": 0.50, "avg_response_time_hours": 24.0,
    "skill_assessment_scores": {}, "connection_count": 80,
    "endorsements_received": 0, "notice_period_days": 30,
    "expected_salary_range_inr_lpa": {"min": 20.0, "max": 30.0},
    "preferred_work_mode": "hybrid", "willing_to_relocate": True,
    "github_activity_score": 10.0, "search_appearance_30d": 50,
    "saved_by_recruiters_30d": 2, "interview_completion_rate": 0.60,
    "offer_acceptance_rate": 0.50, "verified_email": True,
    "verified_phone": True, "linkedin_connected": False
  }
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def render_single_candidate(candidate_data):
    """Render the full 5-layer scorecard for one candidate."""
    profile = candidate_data.get('profile', {})
    cid = candidate_data.get('candidate_id', 'Unknown')
    st.subheader(f"Candidate ID: `{cid}`")
    st.write(
        f"**Name:** {profile.get('anonymized_name', 'N/A')} &nbsp;|&nbsp; "
        f"**Title:** {profile.get('current_title', 'N/A')} &nbsp;|&nbsp; "
        f"**Experience:** {profile.get('years_of_experience', 'N/A')} yrs &nbsp;|&nbsp; "
        f"**Location:** {profile.get('location', 'N/A')}"
    )

    with st.spinner("Scoring…"):
        scores = scoring.score_candidate(candidate_data)

    st.markdown("---")
    st.subheader("📊 Scoring Breakdown")
    col1, col2, col3 = st.columns(3)
    col1.metric("🏆 Composite Score",          f"{scores['composite_score']} / 100")
    col2.metric("💼 Title & Career Fit (40%)", f"{scores['title_career_score']}")
    col3.metric("🛠️ Skills Trust (20%)",       f"{scores['skills_score']}")

    col4, col5, col6 = st.columns(3)
    col4.metric("🏃 Behavioral (20%)",  f"{scores['behavioral_score']}")
    col5.metric("📍 Logistics (10%)",   f"{scores['logistics_score']}")
    col6.metric("🎓 Exp & Edu (10%)",   f"{scores['experience_education_score']}")

    st.markdown("---")
    if scores.get('is_honeypot'):
        st.error("🚨 **HONEYPOT DETECTED** 🚨")
        for reason in scores.get('honeypot_reasons', []):
            st.write(f"- {reason}")
        st.warning("Honeypots receive a 40 % composite-score penalty.")
    else:
        st.success("✅ Passed all honeypot checks.")

    st.markdown("---")
    st.subheader("📝 Generated Reasoning")
    reasoning = scoring.generate_reasoning(candidate_data, scores, 1)
    st.info(reasoning)


def stream_and_rank(file_obj, top_n, max_candidates):
    """
    Stream a JSONL file line-by-line, score every candidate,
    and return the top-N sorted results.  Never loads the whole
    file into RAM at once.
    """
    results = []
    honeypots = []
    seen = 0

    for raw_bytes in file_obj:
        try:
            line = raw_bytes.decode("utf-8", errors="replace").strip() if isinstance(raw_bytes, bytes) else raw_bytes.strip()
        except Exception:
            continue
        if not line:
            continue
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue

        scores = scoring.score_candidate(candidate)
        profile = candidate.get("profile", {})
        row = {
            "Rank":         None,
            "ID":           candidate.get("candidate_id", ""),
            "Name":         profile.get("anonymized_name", "N/A"),
            "Title":        profile.get("current_title", "N/A"),
            "Exp (yrs)":    profile.get("years_of_experience", 0),
            "Location":     profile.get("location", "N/A"),
            "Score":        scores["composite_score"],
            "Career (40%)": scores["title_career_score"],
            "Skills (20%)": scores["skills_score"],
            "Behav (20%)":  scores["behavioral_score"],
            "Logist (10%)": scores["logistics_score"],
            "Edu (10%)":    scores["experience_education_score"],
            "Honeypot":     "🚨 YES" if scores.get("is_honeypot") else "✅ No",
            "_data":        candidate,
            "_scores":      scores,
        }
        if scores.get("is_honeypot"):
            honeypots.append(row)
        else:
            results.append(row)

        seen += 1
        if max_candidates and seen >= max_candidates:
            break

    # Sort by score descending
    results.sort(key=lambda x: -x["Score"])
    top = results[:top_n]
    for i, r in enumerate(top, 1):
        r["Rank"] = i

    return top, honeypots, seen


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Redrob Ranker Sandbox", page_icon="⚖️", layout="wide")
st.title("⚖️ Redrob Candidate Ranker Sandbox")
st.markdown(
    "Evaluate candidates in real-time with our **5-layer heuristic engine**. "
    "Choose **Single Inspector** to deep-dive into one profile, or "
    "**Full Ranking** to rank every candidate in an uploaded JSONL file."
)

# ---------------------------------------------------------------------------
# Sidebar – mode selector
# ---------------------------------------------------------------------------
st.sidebar.header("⚙️ Mode")
mode = st.sidebar.radio("Select Mode:", ("🔍 Single Candidate Inspector", "🏆 Full Ranking Mode"))

# ===========================================================================
# MODE 1 – Single Candidate Inspector
# ===========================================================================
if mode == "🔍 Single Candidate Inspector":
    st.sidebar.markdown("---")
    st.sidebar.subheader("Data Input")

    input_method = st.sidebar.radio(
        "Input source:",
        ("Built-in Sample Profile", "Upload JSONL/JSON File", "Paste Custom JSON")
    )

    candidate_data = None

    if input_method == "Built-in Sample Profile":
        sample_choice = st.sidebar.selectbox(
            "Choose a sample:",
            ("Select…",
             "✅ Ideal Senior AI Engineer (High Match)",
             "⚠️ Operations Manager (Keyword Stuffer)",
             "🚨 Adversarial Profile (Honeypot)")
        )
        if "Ideal" in sample_choice:
            candidate_data = SAMPLE_1
        elif "Keyword" in sample_choice:
            candidate_data = SAMPLE_2
        elif "Honeypot" in sample_choice:
            candidate_data = SAMPLE_3

    elif input_method == "Upload JSONL/JSON File":
        upload = st.sidebar.file_uploader(
            "Upload file (evaluates first candidate only)",
            type=["jsonl", "json"]
        )
        if upload:
            try:
                if upload.size < 10 * 1024 * 1024:
                    content = upload.getvalue().decode("utf-8").strip()
                    try:
                        candidate_data = json.loads(content)
                    except json.JSONDecodeError:
                        candidate_data = json.loads(content.split("\n")[0])
                else:
                    first_line = upload.readline().decode("utf-8").strip()
                    candidate_data = json.loads(first_line)
            except Exception as e:
                st.sidebar.error(f"Parse error: {e}")

    else:
        json_text = st.sidebar.text_area("Paste Candidate JSON:", height=300)
        if json_text:
            try:
                candidate_data = json.loads(json_text)
            except Exception:
                st.sidebar.error("Invalid JSON — please check your input.")

    # If it's a list, take the first element
    if isinstance(candidate_data, list):
        candidate_data = candidate_data[0] if candidate_data else None

    st.header("🔍 Single Candidate Inspector")
    if candidate_data:
        render_single_candidate(candidate_data)
    else:
        st.info("👈 Select a built-in sample, upload a file, or paste JSON in the sidebar.")

# ===========================================================================
# MODE 2 – Full Ranking Mode
# ===========================================================================
else:
    st.header("🏆 Full Ranking Mode")
    st.markdown(
        "Upload a **JSONL file** where every line is one candidate object "
        "(same format as `candidates.jsonl`).  The engine will score **every** "
        "candidate and display a ranked leaderboard."
    )

    # Sidebar controls for ranking
    top_n = st.sidebar.slider("Show top N candidates:", 5, 200, 100, step=5)
    max_cands = st.sidebar.number_input(
        "Max candidates to read (0 = all):", min_value=0, max_value=100000,
        value=0, step=1000,
        help="Set a limit to speed things up. 0 = read the entire file."
    )

    upload = st.sidebar.file_uploader(
        "Upload JSONL file:", type=["jsonl", "json"]
    )

    if upload:
        limit = int(max_cands) if max_cands > 0 else None
        progress_bar = st.progress(0, text="Starting…")
        status_text  = st.empty()

        with st.spinner(f"Scoring candidates… this may take a few minutes for the full 100K file."):
            try:
                top_results, honeypot_list, total_seen = stream_and_rank(
                    upload, top_n=top_n, max_candidates=limit
                )
            except Exception as e:
                st.error(f"Error during ranking: {e}")
                st.stop()

        progress_bar.progress(1.0, text="Done!")
        st.success(
            f"✅ Scored **{total_seen:,}** candidates. "
            f"Found **{len(honeypot_list)}** honeypots. "
            f"Showing top **{len(top_results)}**."
        )

        if not top_results:
            st.warning("No valid candidates found in the file.")
        else:
            # Build display dataframe (hide internal _data/_scores columns)
            display_cols = ["Rank", "ID", "Name", "Title", "Exp (yrs)", "Location",
                            "Score", "Career (40%)", "Skills (20%)",
                            "Behav (20%)", "Logist (10%)", "Edu (10%)", "Honeypot"]
            display_rows = [{k: r[k] for k in display_cols} for r in top_results]

            st.subheader(f"📋 Top {len(top_results)} Ranked Candidates")
            st.dataframe(display_rows, use_container_width=True, height=500)

            # CSV download
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=display_cols)
            writer.writeheader()
            writer.writerows(display_rows)
            st.download_button(
                "⬇️ Download Leaderboard CSV",
                data=buf.getvalue(),
                file_name="sandbox_ranking.csv",
                mime="text/csv"
            )

            # Drill-down into individual candidate
            st.markdown("---")
            st.subheader("🔎 Drill-down: Inspect a Candidate")
            candidate_ids = [r["ID"] for r in top_results]
            selected_id = st.selectbox("Select a Candidate ID to inspect:", candidate_ids)
            selected = next(r for r in top_results if r["ID"] == selected_id)
            render_single_candidate(selected["_data"])

        # Honeypot summary
        if honeypot_list:
            st.markdown("---")
            with st.expander(f"🚨 Honeypots Detected ({len(honeypot_list)}) — click to expand"):
                hp_cols = ["ID", "Name", "Title", "Score"]
                hp_rows = [{k: r[k] for k in hp_cols} for r in honeypot_list]
                st.dataframe(hp_rows, use_container_width=True)
    else:
        st.info(
            "👈 Upload a JSONL file in the sidebar to begin ranking.\n\n"
            "**Tip:** For a quick demo, switch to **Single Candidate Inspector** "
            "and pick a built-in sample — no file upload needed!"
        )
