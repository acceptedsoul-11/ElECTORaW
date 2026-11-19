
from pathlib import Path
from difflib import SequenceMatcher

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"

unmatched_file = PROCESSED / "official_winners_unmatched.csv"
candidates_file = PROCESSED / "candidate_import_preview.csv"

unmatched = pd.read_csv(unmatched_file).fillna("")
candidates = pd.read_csv(candidates_file).fillna("")


def norm(value):
    """Normalize names while ignoring punctuation and case."""
    text = str(value).casefold()
    return " ".join(
        "".join(ch if ch.isalnum() else " " for ch in text).split()
    )


def similarity(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


reports = []

for _, winner in unmatched.iterrows():
    year = int(winner["year"])
    state = norm(winner["state"])
    constituency = norm(winner["constituency"])
    name = norm(winner["winner"])

    year_candidates = candidates[
        candidates["election_year"].astype(int) == year
    ].copy()

    year_candidates["_state"] = year_candidates["state_name"].map(norm)
    year_candidates["_constituency"] = (
        year_candidates["constituency_name"].map(norm)
    )
    year_candidates["_name"] = year_candidates["candidate_name"].map(norm)

    # Prefer candidates from the same state.
    same_state = year_candidates[
        year_candidates["_state"] == state
    ].copy()

    if same_state.empty:
        same_state = year_candidates.copy()

    same_state["_name_score"] = same_state["_name"].map(
        lambda candidate_name: similarity(name, candidate_name)
    )
    same_state["_constituency_score"] = same_state[
        "_constituency"
    ].map(lambda candidate_constituency: similarity(
        constituency, candidate_constituency
    ))

    # Combine name and constituency similarity.
    same_state["_combined_score"] = (
        0.75 * same_state["_name_score"]
        + 0.25 * same_state["_constituency_score"]
    )

    # Exact state/constituency candidates should rank first.
    same_state["_same_constituency"] = (
        same_state["_constituency"] == constituency
    )

    top = same_state.sort_values(
        ["_same_constituency", "_combined_score"],
        ascending=[False, False],
    ).head(5)

    if top.empty:
        reports.append({
            "year": year,
            "state": winner["state"],
            "official_constituency": winner["constituency"],
            "official_winner": winner["winner"],
            "official_party": winner["party"],
            "candidate_name": "",
            "candidate_state": "",
            "candidate_constituency": "",
            "candidate_party": "",
            "name_similarity": 0,
            "constituency_similarity": 0,
            "combined_score": 0,
        })
        continue

    for _, candidate in top.iterrows():
        reports.append({
            "year": year,
            "state": winner["state"],
            "official_constituency": winner["constituency"],
            "official_winner": winner["winner"],
            "official_party": winner["party"],
            "candidate_name": candidate["candidate_name"],
            "candidate_state": candidate["state_name"],
            "candidate_constituency": candidate["constituency_name"],
            "candidate_party": candidate["party_name_source"],
            "name_similarity": round(
                candidate["_name_score"], 3
            ),
            "constituency_similarity": round(
                candidate["_constituency_score"], 3
            ),
            "combined_score": round(
                candidate["_combined_score"], 3
            ),
        })

output = PROCESSED / "unmatched_winner_diagnostics.csv"
pd.DataFrame(reports).to_csv(output, index=False)

print(f"Unmatched official winners examined: {len(unmatched)}")
print(f"Candidate comparison rows: {len(reports)}")
print(f"Saved diagnostic report: {output}")

print("\nTOP CANDIDATE SUGGESTIONS")
print("=" * 100)

for _, winner in unmatched.iterrows():
    subset = pd.DataFrame(reports)
    subset = subset[
        (subset["year"] == int(winner["year"]))
        & (subset["state"] == winner["state"])
        & (subset["official_constituency"] == winner["constituency"])
        & (subset["official_winner"] == winner["winner"])
    ].head(3)

    print(
        f"\n{int(winner['year'])} | {winner['state']} | "
        f"{winner['constituency']} | {winner['winner']}"
    )

    if subset.empty:
        print("  No candidate suggestions found.")
    else:
        for _, item in subset.iterrows():
            print(
                f"  Candidate: {item['candidate_name']} | "
                f"Constituency: {item['candidate_constituency']} | "
                f"Party: {item['candidate_party']} | "
                f"Name score: {item['name_similarity']} | "
                f"Constituency score: "
                f"{item['constituency_similarity']}"
            )
