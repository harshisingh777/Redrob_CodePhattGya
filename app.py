import streamlit as st
import json
import scoring

# Pre-defined sample profiles to allow instant evaluation without file upload
SAMPLE_1 = {
  "candidate_id": "CAND_IDEAL_01",
  "profile": {
    "anonymized_name": "Aarav Sharma",
    "headline": "Senior ML Engineer | Search & Retrieval | RAG & Vector DBs",
    "summary": "Senior Machine Learning Engineer with 7 years of experience specializing in search, recommendation systems, and large language models. Shipped embeddings-based retrieval systems using FAISS and Milvus to production. Highly proficient in Python and PyTorch.",
    "location": "Pune",
    "country": "India",
    "years_of_experience": 7.0,
    "current_title": "Senior Machine Learning Engineer",
    "current_company": "InnoTech",
    "current_company_size": "201-500",
    "current_industry": "Software Products"
  },
  "career_history": [
    {
      "company": "InnoTech",
      "title": "Senior Machine Learning Engineer",
      "start_date": "2023-01-10",
      "end_date": None,
      "duration_months": 41,
      "is_current": True,
      "industry": "Software Products",
      "company_size": "201-500",
      "description": "Led the development of a hybrid search and recommendation engine. Implemented embeddings-based retrieval using Milvus and optimized search ranking models, improving NDCG@10 by 14%. Designed evaluation frameworks (MRR, NDCG)."
    },
    {
      "company": "DataFlow Labs",
      "title": "ML Engineer",
      "start_date": "2019-06-01",
      "end_date": "2022-12-31",
      "duration_months": 43,
      "is_current": False,
      "industry": "Software Products",
      "company_size": "51-200",
      "description": "Built and deployed NLP pipelines and fine-tuned BERT models for customer support ticket routing. Set up Pinecone vector databases for semantic search."
    }
  ],
  "education": [
    {
      "institution": "Indian Institute of Technology Bombay",
      "degree": "B.Tech.",
      "field_of_study": "Computer Science",
      "start_year": 2015,
      "end_year": 2019,
      "grade": "8.8/10 CPI",
      "tier": "tier_1"
    }
  ],
  "skills": [
    {"name": "Python", "proficiency": "expert", "endorsements": 85, "duration_months": 80},
    {"name": "Milvus", "proficiency": "expert", "endorsements": 42, "duration_months": 36},
    {"name": "Vector Databases", "proficiency": "expert", "endorsements": 30, "duration_months": 36},
    {"name": "PyTorch", "proficiency": "expert", "endorsements": 55, "duration_months": 48},
    {"name": "NDCG", "proficiency": "advanced", "endorsements": 15, "duration_months": 24}
  ],
  "redrob_signals": {
    "profile_completeness_score": 95.0,
    "signup_date": "2024-01-01",
    "last_active_date": "2026-06-05",
    "open_to_work_flag": True,
    "profile_views_received_30d": 45,
    "applications_submitted_30d": 1,
    "recruiter_response_rate": 0.85,
    "avg_response_time_hours": 12.0,
    "skill_assessment_scores": {
      "Python": 88.0,
      "Milvus": 82.0
    },
    "connection_count": 520,
    "endorsements_received": 180,
    "notice_period_days": 15,
    "expected_salary_range_inr_lpa": {"min": 35.0, "max": 50.0},
    "preferred_work_mode": "hybrid",
    "willing_to_relocate": True,
    "github_activity_score": 75.0,
    "search_appearance_30d": 350,
    "saved_by_recruiters_30d": 15,
    "interview_completion_rate": 0.90,
    "offer_acceptance_rate": 0.75,
    "verified_email": True,
    "verified_phone": True,
    "linkedin_connected": True
  }
}

SAMPLE_2 = {
  "candidate_id": "CAND_STUFFER_02",
  "profile": {
    "anonymized_name": "Saanvi Sethi",
    "headline": "Operations Manager | Expert in PyTorch, Milvus, LLMs",
    "summary": "Experienced Operations Manager with 12 years of leadership in IT services. Recently gained certifications in AI/ML and completed tutorials in vector databases and fine-tuning LLMs.",
    "location": "Chennai",
    "country": "India",
    "years_of_experience": 12.5,
    "current_title": "Operations Manager",
    "current_company": "Wipro",
    "current_company_size": "10001+",
    "current_industry": "IT Services"
  },
  "career_history": [
    {
      "company": "Wipro",
      "title": "Operations Manager",
      "start_date": "2022-11-14",
      "end_date": None,
      "duration_months": 43,
      "is_current": True,
      "industry": "IT Services",
      "company_size": "10001+",
      "description": "Managed customer support operations and teams. Handled escalation processes. Lighter on technical depth."
    }
  ],
  "education": [
    {
      "institution": "Lovely Professional University",
      "degree": "B.B.A.",
      "field_of_study": "Business Administration",
      "start_year": 2010,
      "end_year": 2013,
      "grade": "7.5 CGPA",
      "tier": "tier_3"
    }
  ],
  "skills": [
    {"name": "Python", "proficiency": "expert", "endorsements": 0, "duration_months": 2},
    {"name": "Milvus", "proficiency": "expert", "endorsements": 0, "duration_months": 1},
    {"name": "PyTorch", "proficiency": "expert", "endorsements": 0, "duration_months": 1},
    {"name": "Fine-tuning LLMs", "proficiency": "expert", "endorsements": 0, "duration_months": 1}
  ],
  "redrob_signals": {
    "profile_completeness_score": 70.0,
    "signup_date": "2025-05-01",
    "last_active_date": "2026-05-15",
    "open_to_work_flag": True,
    "profile_views_received_30d": 5,
    "applications_submitted_30d": 12,
    "recruiter_response_rate": 0.20,
    "avg_response_time_hours": 150.0,
    "skill_assessment_scores": {},
    "connection_count": 120,
    "endorsements_received": 5,
    "notice_period_days": 90,
    "expected_salary_range_inr_lpa": {"min": 15.0, "max": 25.0},
    "preferred_work_mode": "onsite",
    "willing_to_relocate": False,
    "github_activity_score": 2.0,
    "search_appearance_30d": 20,
    "saved_by_recruiters_30d": 1,
    "interview_completion_rate": 0.40,
    "offer_acceptance_rate": 0.50,
    "verified_email": True,
    "verified_phone": True,
    "linkedin_connected": False
  }
}

SAMPLE_3 = {
  "candidate_id": "CAND_HONEYPOT_03",
  "profile": {
    "anonymized_name": "Suspicious Dev",
    "headline": "AI Guru | Shipped Milvus, FAISS, PyTorch Systems",
    "summary": "AI Engineer with 5 years experience. Expert in all things AI.",
    "location": "Noida",
    "country": "India",
    "years_of_experience": 5.0,
    "current_title": "AI Lead",
    "current_company": "Startup X",
    "current_company_size": "11-50",
    "current_industry": "Software Products"
  },
  "career_history": [
    {
      "company": "Startup X",
      "title": "AI Lead",
      "start_date": "2025-01-01",
      "end_date": "2025-10-31",
      "duration_months": 60,
      "is_current": False,
      "industry": "Software Products",
      "description": "Built AI retrieval systems. Note the duration of 60 months at a job lasting only 10 months calendar time."
    }
  ],
  "education": [
    {
      "institution": "Amity University",
      "degree": "B.Tech.",
      "field_of_study": "Computer Science",
      "start_year": 2016,
      "end_year": 2020,
      "grade": "8.0",
      "tier": "tier_3"
    }
  ],
  "skills": [
    {"name": "Python", "proficiency": "expert", "endorsements": 0, "duration_months": 1},
    {"name": "PyTorch", "proficiency": "expert", "endorsements": 0, "duration_months": 2},
    {"name": "Milvus", "proficiency": "expert", "endorsements": 0, "duration_months": 1},
    {"name": "FAISS", "proficiency": "expert", "endorsements": 0, "duration_months": 1},
    {"name": "NLP", "proficiency": "expert", "endorsements": 0, "duration_months": 1},
    {"name": "Embeddings", "proficiency": "expert", "endorsements": 0, "duration_months": 1}
  ],
  "redrob_signals": {
    "profile_completeness_score": 80.0,
    "signup_date": "2025-11-01",
    "last_active_date": "2026-05-30",
    "open_to_work_flag": True,
    "profile_views_received_30d": 12,
    "applications_submitted_30d": 4,
    "recruiter_response_rate": 0.50,
    "avg_response_time_hours": 24.0,
    "skill_assessment_scores": {},
    "connection_count": 80,
    "endorsements_received": 0,
    "notice_period_days": 30,
    "expected_salary_range_inr_lpa": {"min": 20.0, "max": 30.0},
    "preferred_work_mode": "hybrid",
    "willing_to_relocate": True,
    "github_activity_score": 10.0,
    "search_appearance_30d": 50,
    "saved_by_recruiters_30d": 2,
    "interview_completion_rate": 0.60,
    "offer_acceptance_rate": 0.50,
    "verified_email": True,
    "verified_phone": True,
    "linkedin_connected": False
  }
}

st.set_page_config(page_title="Redrob Ranker Sandbox", page_icon="⚖️", layout="wide")

st.title("⚖️ Redrob Candidate Ranker Sandbox")
st.markdown("""
Welcome to the Redrob Ranker Sandbox! 
Select a built-in profile, upload a candidate JSON/JSONL, or paste one below to see how our **5-layer heuristic engine** evaluates it in real-time.
""")

st.sidebar.header("Data Input")

input_method = st.sidebar.radio(
    "Select Input Method:",
    ("Use Built-in Sample Profile", "Upload JSONL/JSON File", "Paste Custom JSON")
)

candidate_data = None

if input_method == "Use Built-in Sample Profile":
    sample_choice = st.sidebar.selectbox(
        "Choose a Sample Profile:",
        ("Select a sample...", "Ideal Senior AI Engineer (High Match)", "Operations Manager (Keyword Stuffer)", "Adversarial Profile (Honeypot)")
    )
    if sample_choice == "Ideal Senior AI Engineer (High Match)":
        candidate_data = SAMPLE_1
    elif sample_choice == "Operations Manager (Keyword Stuffer)":
        candidate_data = SAMPLE_2
    elif sample_choice == "Adversarial Profile (Honeypot)":
        candidate_data = SAMPLE_3

elif input_method == "Upload JSONL/JSON File":
    upload = st.sidebar.file_uploader("Upload JSONL/JSON (evaluates first candidate)", type=["jsonl", "json"])
    if upload:
        try:
            # Check size of the uploaded file
            if upload.size < 10 * 1024 * 1024:  # Less than 10MB, safe to parse entirely
                content = upload.getvalue().decode("utf-8").strip()
                try:
                    candidate_data = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback: try reading the first line as JSONL
                    first_line = content.split('\n')[0]
                    candidate_data = json.loads(first_line)
            else:
                # Large file (>10MB): read only the first line to prevent out-of-memory crashes
                first_line_bytes = upload.readline()
                first_line = first_line_bytes.decode("utf-8").strip()
                candidate_data = json.loads(first_line)
        except Exception as e:
            st.sidebar.error(f"Error parsing upload: {e}")

elif input_method == "Paste Custom JSON":
    json_text = st.sidebar.text_area("Paste Candidate JSON here:", height=300)
    if json_text:
        try:
            candidate_data = json.loads(json_text)
        except Exception as e:
            st.sidebar.error(f"Invalid JSON format.")

# Extract the first candidate if the input data is a list/array of candidates
if candidate_data:
    if isinstance(candidate_data, list):
        if len(candidate_data) > 0:
            candidate_data = candidate_data[0]
        else:
            candidate_data = None
            st.sidebar.error("The JSON list is empty.")

if candidate_data:
    st.header("Evaluating Candidate")
    
    profile = candidate_data.get('profile', {})
    st.subheader(f"Candidate ID: `{candidate_data.get('candidate_id', 'Unknown')}`")
    st.write(f"**Current Title:** {profile.get('current_title', 'N/A')} | **Experience:** {profile.get('years_of_experience', 'N/A')} years")
    
    with st.spinner("Scoring..."):
        scores = scoring.score_candidate(candidate_data)
        
    st.markdown("---")
    st.subheader("Scoring Breakdown")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🏆 Composite Score", f"{scores['composite_score']} / 100")
    col2.metric("💼 Title & Career Fit (40%)", f"{scores['title_career_score']}")
    col3.metric("🛠️ Skills Trust (20%)", f"{scores['skills_score']}")
    
    col4, col5, col6 = st.columns(3)
    col4.metric("🏃 Behavioral Availability (20%)", f"{scores['behavioral_score']}")
    col5.metric("📍 Logistics Fit (10%)", f"{scores['logistics_score']}")
    col6.metric("🎓 Experience & Education (10%)", f"{scores['experience_education_score']}")
    
    st.markdown("---")
    
    if scores.get('is_honeypot'):
        st.error("🚨 **HONEYPOT DETECTED** 🚨")
        for reason in scores.get('honeypot_reasons', []):
            st.write(f"- {reason}")
        st.warning("Note: Honeypots receive a 40% composite score penalty.")
    else:
        st.success("✅ Passed all honeypot checks.")
        
    st.markdown("---")
    st.subheader("Generated Reasoning")
    reasoning = scoring.generate_reasoning(candidate_data, scores, 1)
    st.info(reasoning)
    
else:
    st.info("👈 Please select a built-in sample profile, upload a JSONL file, or paste candidate JSON in the sidebar to begin.")
