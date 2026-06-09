#!/usr/bin/env python3
"""
Redrob AI Hackathon — Intelligent Candidate Discovery & Ranking
================================================================
Main entry point for the candidate ranking pipeline.

Loads candidates from JSONL, scores them using a multi-layer scoring engine,
filters honeypots, and outputs a ranked CSV submission file.

Usage:
    python rank.py --candidates ./candidates.jsonl --out ./submission.csv
"""

import argparse
import csv
import gzip
import json
import os
import sys
import time


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Redrob AI Hackathon — Rank candidates for Senior AI Engineer position",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python rank.py --candidates ./candidates.jsonl --out ./submission.csv\n"
            "  python rank.py --candidates ./candidates.jsonl.gz\n"
        ),
    )
    parser.add_argument(
        "--candidates",
        required=True,
        help="Path to candidates file (.jsonl or .jsonl.gz)",
    )
    parser.add_argument(
        "--out",
        default="submission.csv",
        help="Output CSV path (default: submission.csv)",
    )
    return parser.parse_args()


def load_candidates(filepath: str) -> list[dict]:
    """
    Load all candidates from a JSONL file (plain or gzipped).

    Args:
        filepath: Path to .jsonl or .jsonl.gz file.

    Returns:
        List of candidate dictionaries.
    """
    candidates = []
    if not os.path.exists(filepath):
        print(f"ERROR: Candidates file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    is_gzipped = filepath.endswith(".gz")
    open_fn = gzip.open if is_gzipped else open
    open_kwargs = {"mode": "rt", "encoding": "utf-8"}

    print(f"Loading candidates from: {filepath}")
    print(f"  Format: {'gzipped JSONL' if is_gzipped else 'plain JSONL'}")

    with open_fn(filepath, **open_kwargs) as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                candidate = json.loads(line)
                candidates.append(candidate)
            except json.JSONDecodeError as e:
                print(f"  WARNING: Skipping malformed JSON on line {i}: {e}", file=sys.stderr)

            if len(candidates) % 10_000 == 0:
                print(f"  Loaded {len(candidates):,} candidates...")

    print(f"  Total candidates loaded: {len(candidates):,}")
    return candidates


def score_all_candidates(candidates: list[dict]) -> list[dict]:
    """
    Score every candidate using the multi-layer scoring engine.

    Args:
        candidates: List of raw candidate dictionaries.

    Returns:
        List of dicts, each containing the candidate data and its scores.
    """
    from scoring import score_candidate

    scored = []
    total = len(candidates)
    print(f"\nScoring {total:,} candidates...")

    for i, candidate in enumerate(candidates, start=1):
        scores = score_candidate(candidate)
        scored.append({"candidate": candidate, "scores": scores})

        if i % 10_000 == 0:
            print(f"  Scored {i:,} / {total:,} candidates...")

    print(f"  Scoring complete: {total:,} candidates processed.")
    return scored


def filter_and_rank(scored_candidates: list[dict]) -> tuple[list[dict], int]:
    """
    Filter out honeypot candidates, sort by composite score, and return top 100.

    Sorting:
        - Primary: composite_score descending
        - Tie-break: candidate_id ascending (deterministic)

    Args:
        scored_candidates: List of scored candidate dicts.

    Returns:
        Tuple of (top_100 ranked list, honeypot_count).
    """
    honeypots = [s for s in scored_candidates if s["scores"]["is_honeypot"]]
    genuine = [s for s in scored_candidates if not s["scores"]["is_honeypot"]]

    honeypot_count = len(honeypots)
    print(f"\nFiltering results:")
    print(f"  Honeypots detected: {honeypot_count:,}")
    print(f"  Genuine candidates: {len(genuine):,}")

    # Sort: highest composite_score first, then candidate_id ascending for ties
    genuine.sort(
        key=lambda s: (
            -s["scores"]["composite_score"],
            str(s["candidate"].get("candidate_id", "")),
        )
    )

    top_100 = genuine[:100]
    return top_100, honeypot_count


def write_submission(top_100: list[dict], output_path: str) -> None:
    """
    Write the final ranked CSV submission file.

    CSV columns: candidate_id, rank, score, reasoning
        - rank: 1–100
        - score: composite_score / 100, 4 decimal places, non-increasing
        - reasoning: generated explanation string

    Args:
        top_100: Ranked list of top candidate dicts.
        output_path: Path for the output CSV file.
    """
    from scoring import generate_reasoning

    print(f"\nGenerating reasoning and writing submission to: {output_path}")

    # Ensure output directory exists
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        for rank, entry in enumerate(top_100, start=1):
            candidate = entry["candidate"]
            scores = entry["scores"]
            candidate_id = candidate.get("candidate_id", "")

            # Normalize score to 0–1 range with 4 decimal places
            normalized_score = round(scores["composite_score"] / 100.0, 4)

            # Generate reasoning for this candidate
            reasoning = generate_reasoning(candidate, scores, rank)

            writer.writerow([candidate_id, rank, f"{normalized_score:.4f}", reasoning])

    print(f"  Submission written: {len(top_100)} candidates ranked.")


def print_summary(top_100: list[dict], total_loaded: int, honeypot_count: int) -> None:
    """Print summary statistics and a preview of the top 10 candidates."""
    print("\n" + "=" * 70)
    print("RANKING SUMMARY")
    print("=" * 70)
    print(f"  Total candidates loaded:  {total_loaded:,}")
    print(f"  Honeypots detected:       {honeypot_count:,}")
    print(f"  Genuine candidates:       {total_loaded - honeypot_count:,}")
    print(f"  Top candidates ranked:    {len(top_100)}")

    print(f"\n  {'Rank':<6} {'Candidate ID':<40} {'Score':<10} {'Composite':<10}")
    print(f"  {'-'*6} {'-'*40} {'-'*10} {'-'*10}")

    for rank, entry in enumerate(top_100[:10], start=1):
        cid = str(entry["candidate"].get("candidate_id", ""))[:38]
        composite = entry["scores"]["composite_score"]
        normalized = composite / 100.0
        print(f"  {rank:<6} {cid:<40} {normalized:<10.4f} {composite:<10.2f}")

    if len(top_100) > 10:
        print(f"  ... and {len(top_100) - 10} more candidates")
    print("=" * 70)


def main():
    """Main pipeline entry point."""
    args = parse_args()
    start_time = time.time()

    print("=" * 70)
    print("Redrob AI Hackathon — Candidate Ranking Pipeline")
    print("=" * 70)

    # Step 1: Load candidates
    candidates = load_candidates(args.candidates)
    if not candidates:
        print("ERROR: No candidates loaded. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Step 2: Score all candidates
    scored = score_all_candidates(candidates)

    # Step 3: Filter honeypots and rank
    top_100, honeypot_count = filter_and_rank(scored)

    if not top_100:
        print("ERROR: No genuine candidates found after filtering. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Step 4: Write submission CSV
    write_submission(top_100, args.out)

    # Step 5: Print summary
    print_summary(top_100, len(candidates), honeypot_count)

    # Runtime
    elapsed = time.time() - start_time
    minutes, seconds = divmod(elapsed, 60)
    print(f"\n  Total runtime: {int(minutes)}m {seconds:.1f}s")
    print(f"  Output file:   {os.path.abspath(args.out)}")
    print()


if __name__ == "__main__":
    main()
