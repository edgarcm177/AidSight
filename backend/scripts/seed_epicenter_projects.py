#!/usr/bin/env python3
"""
Seed project data so Success Twin has at least 2 projects per epicenter country.

The app loads projects from data/projects.parquet (via the root-level data package).
Epicenter countries in the UI are MLI, BFA, NER, TCD. If any have < 2 projects,
Success Twin by epicenter will 404.

Run from repo root:
  python -m backend.scripts.seed_epicenter_projects

This reads data/projects.parquet, adds synthetic projects for any epicenter
with < 2 projects, and overwrites the file.
"""

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECTS_PARQUET = REPO_ROOT / "data" / "projects.parquet"

EPICENTER_COUNTRIES = ["MLI", "BFA", "NER", "TCD"]

# Two distinct descriptions per country so twins are semantically similar but not identical
SECTOR_TEMPLATES = [
    ("Health", "Emergency health services and trauma care for conflict-affected populations in the Sahel."),
    ("WASH", "Water, sanitation, and hygiene promotion in displacement sites and host communities."),
    ("Protection", "Child protection and GBV response in refugee hosting areas and border regions."),
    ("Food Security", "Food distribution and cash assistance for food-insecure families and IDPs."),
    ("Shelter", "Emergency shelter and NFI kits for internally displaced populations."),
    ("Education", "Temporary learning spaces and teacher training in crisis-affected zones."),
]


def main() -> None:
    if not PROJECTS_PARQUET.exists():
        print(f"Not found: {PROJECTS_PARQUET}", file=sys.stderr)
        print("Create it first (e.g. run backend/scripts/preprocess and copy to data/, or create from sample).", file=sys.stderr)
        sys.exit(1)

    df = pd.read_parquet(PROJECTS_PARQUET)
    existing_ids = set(df["id"].astype(str))
    next_num = max((int(str(i).replace("PRJ", "")) for i in existing_ids if str(i).startswith("PRJ") and str(i)[3:].isdigit()), default=0) + 1

    country_col = df["country"].astype(str).str.strip().str.upper()
    added = []
    for country in EPICENTER_COUNTRIES:
        count = (country_col == country).sum()
        need = max(0, 2 - count)
        for k in range(need):
            sid = next_num
            next_num += 1
            project_id = f"PRJ{sid:03d}"
            sector, description = SECTOR_TEMPLATES[(sid + ord(country[0])) % len(SECTOR_TEMPLATES)]
            budget = 600_000 + (sid * 70_000) % 2_500_000
            beneficiaries = 8_000 + (sid * 500) % 40_000
            cost_pb = budget / beneficiaries if beneficiaries > 0 else float("nan")
            row = {
                "id": project_id,
                "name": f"{sector} project {country} 2024",
                "country": country,
                "year": 2024,
                "sector": sector,
                "description": description,
                "budget": float(budget),
                "beneficiaries": int(beneficiaries),
                "cost_per_beneficiary": cost_pb,
                "robust_under_shock": sid % 4 == 0,
            }
            added.append(row)

    if not added:
        print("All epicenter countries (MLI, BFA, NER, TCD) already have at least 2 projects. Nothing to do.")
        return

    extra = pd.DataFrame(added)
    out = pd.concat([df, extra], ignore_index=True)
    out.to_parquet(PROJECTS_PARQUET, index=False)
    print(f"Added {len(added)} project(s) to {PROJECTS_PARQUET}")
    for c in EPICENTER_COUNTRIES:
        n = (out["country"].astype(str).str.upper() == c).sum()
        print(f"  {c}: {n} project(s)")


if __name__ == "__main__":
    main()
