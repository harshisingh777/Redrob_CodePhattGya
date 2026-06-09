import streamlit as st
import json
import scoring

st.set_page_config(page_title="Redrob Ranker Sandbox", page_icon="⚖️", layout="wide")

st.title("⚖️ Redrob Candidate Ranker Sandbox")
st.markdown("""
Welcome to the Redrob Ranker Sandbox! 
Upload a candidate JSON or paste one below to see how our **5-layer heuristic engine** evaluates it in real-time.
""")

st.sidebar.header("Data Input")
upload = st.sidebar.file_uploader("Upload JSONL (evaluates first candidate)", type=["jsonl", "json"])
json_text = st.sidebar.text_area("Or paste Candidate JSON here:", height=300)

candidate_data = None

if upload:
    try:
        # Read only the first line to prevent loading the entire large file into memory
        first_line_bytes = upload.readline()
        first_line = first_line_bytes.decode("utf-8").strip()
        candidate_data = json.loads(first_line)
    except Exception as e:
        st.sidebar.error(f"Error parsing upload: {e}")

elif json_text:
    try:
        candidate_data = json.loads(json_text)
    except Exception as e:
        st.sidebar.error("Invalid JSON format.")

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
    st.info("👈 Please upload a candidate JSONL file or paste JSON data in the sidebar to begin.")
