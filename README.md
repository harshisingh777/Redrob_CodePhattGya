# Redrob AI Hackathon — Intelligent Candidate Discovery & Ranking

An intelligent, multi-layer scoring pipeline that identifies the **top 100 candidates** for a Senior AI/ML Engineer position from a pool of 100,000 applicants — while detecting and filtering honeypot (adversarial) profiles.

---

## Overview

This system processes a large candidate dataset (JSONL format), evaluates each candidate against a detailed job description for a **Senior AI Engineer** role, and produces a ranked shortlist as a CSV submission file.

Key capabilities:
- **Multi-dimensional scoring** across 5 independent evaluation layers
- **Honeypot detection** to automatically filter adversarial/fake candidate profiles
- **Deterministic ranking** with tie-breaking for reproducible results
- **Zero external dependencies** — runs entirely on Python standard library

---

## Architecture

### Multi-Layer Scoring Model

Each candidate is evaluated across five scoring dimensions, weighted to reflect hiring priorities:

| Layer                      | Weight | What It Measures                                                        |
|----------------------------|--------|-------------------------------------------------------------------------|
| **Career & Title Fit**     | 40%    | Job title relevance, career progression, seniority alignment            |
| **Skills Match**           | 20%    | Technical skill overlap with JD requirements (ML, Python, cloud, etc.)  |
| **Behavioral Indicators**  | 20%    | Leadership signals, communication quality, cultural fit markers         |
| **Logistics**              | 10%    | Location compatibility, visa/work authorization, availability           |
| **Experience & Education** | 10%    | Years of experience, degree relevance, institution quality              |

**Final Score** = weighted combination of all layers, normalized to 0–100.

### Honeypot Detection

The system identifies and filters adversarial profiles that exhibit suspicious patterns:
- Impossibly perfect skill coverage across unrelated domains
- Inconsistent experience timelines (e.g., 30 years of experience at age 25)
- Copy-paste or template-generated profile text
- Contradictory information across profile sections
- Unrealistic combinations of qualifications

Detected honeypots are excluded from the final ranking and reported in the summary.

---

## Quick Start

### Prerequisites

- **Python 3.8+** (no external packages required)
- Candidates data file (`candidates.jsonl` or `candidates.jsonl.gz`)

### Run the Pipeline

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

For gzipped input:

```bash
python rank.py --candidates ./candidates.jsonl.gz --out ./submission.csv
```

### Validate the Submission

```bash
python validate_submission.py submission.csv
```

---

## How Scoring Works

### 1. Career & Title Fit (40%)

Evaluates how well the candidate's current and past job titles align with the Senior AI Engineer role. Considers:
- Direct title matches (e.g., "ML Engineer", "AI Researcher")
- Career trajectory and seniority level
- Relevance of domain experience

### 2. Skills Match (20%)

Measures overlap between the candidate's listed skills and the JD's required/preferred skills:
- Core ML/AI frameworks (PyTorch, TensorFlow, scikit-learn)
- Programming languages (Python, SQL)
- Cloud platforms and MLOps tools
- Specialized skills (NLP, computer vision, LLMs)

### 3. Behavioral Indicators (20%)

Analyzes soft signals of candidate quality:
- Leadership and mentorship experience
- Communication clarity in profile text
- Evidence of collaboration and teamwork
- Cultural fit indicators

### 4. Logistics (10%)

Practical compatibility checks:
- Location and remote work compatibility
- Work authorization status
- Notice period and availability

### 5. Experience & Education (10%)

Quantitative background assessment:
- Total years of relevant experience
- Educational background and degree level
- Institution reputation (when available)

---

## Compute Constraints

This solution is designed to meet strict hackathon compute limits:

| Constraint        | Limit     | Our Solution                          |
|-------------------|-----------|---------------------------------------|
| **Runtime**       | < 5 min   | Pure Python, single-pass scoring      |
| **Memory**        | < 16 GB   | Streaming-friendly JSONL loading      |
| **GPU**           | None      | No GPU or ML inference required       |
| **Network**       | None      | Fully offline — no API calls          |
| **Dependencies**  | Minimal   | Python standard library only          |

---

## Project Structure

```
redrob-ranker/
├── rank.py                 # Main entry point — CLI pipeline
├── scoring.py              # Multi-layer scoring engine & honeypot detection
├── requirements.txt        # Dependencies (none — stdlib only)
├── validate_submission.py  # Submission format validator
├── README.md               # This file
├── candidates.jsonl        # Input data (not included in repo)
└── submission.csv          # Output (generated by rank.py)
```

---

## Output Format

The output CSV (`submission.csv`) contains exactly 100 rows:

| Column         | Description                                         |
|----------------|-----------------------------------------------------|
| `candidate_id` | Unique identifier for the candidate                 |
| `rank`         | Rank position (1 = best, 100 = 100th best)         |
| `score`        | Normalized score in [0, 1] range, 4 decimal places  |
| `reasoning`    | Human-readable explanation of the ranking decision   |

Scores are **non-increasing** with rank. Ties are broken by `candidate_id` ascending for deterministic output.

---

## License

Built for the Redrob AI Hackathon.
