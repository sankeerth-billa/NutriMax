"""
NutriMax — Kroger + USDA Nutrition Enrichment
==============================================
The Kroger public API sometimes doesn't include nutrition facts.
This script fuzzy-matches Kroger product names to USDA FoodData Central
entries to fill in the missing nutrition data.

Run AFTER kroger_pipeline.py:
  pip install requests pandas thefuzz python-Levenshtein
  python kroger_enrich_nutrition.py \
    --kroger kroger_grocery.csv \
    --usda-key YOUR_USDA_KEY \
    --output grocery_data_enriched.js

Get a free USDA API key at: https://fdc.nal.usda.gov/api-guide.html
"""

import os
import sys
import json
import time
import argparse
import requests
import pandas as pd

try:
    from thefuzz import fuzz, process
except ImportError:
    print("Install thefuzz: pip install thefuzz python-Levenshtein")
    sys.exit(1)

USDA_API_BASE = "https://api.nal.usda.gov/fdc/v1"
NUTRIENT_IDS  = {
    1008: "cal",
    1003: "protein_g",
    1079: "fiber_g",
    1004: "fat_g",
    1005: "carbs_g",
    1106: "vitA_mcg",
    1162: "vitC_mg",
}

WEIGHTS  = {"protein_g": 0.40, "fiber_g": 0.25, "cal": 0.20, "vitC_mg": 0.08, "vitA_mcg": 0.07}
NORM_MAX = {"protein_g": 30.0, "fiber_g": 15.0, "cal": 400.0, "vitC_mg": 90.0, "vitA_mcg": 900.0}


def usda_search(api_key: str, query: str) -> dict | None:
    """Search USDA FDC for a food item and return nutrient values."""
    try:
        resp = requests.get(
            f"{USDA_API_BASE}/foods/search",
            params={"api_key": api_key, "query": query, "dataType": "Foundation,SR Legacy", "pageSize": 5},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        foods = resp.json().get("foods", [])
        if not foods:
            return None

        # Pick the best fuzzy match among top 5 results
        descriptions = [f["description"] for f in foods]
        best_match, score = process.extractOne(query, descriptions, scorer=fuzz.token_sort_ratio)
        if score < 40:
            return None

        food = foods[descriptions.index(best_match)]
        nutrients = {}
        for n in food.get("foodNutrients", []):
            nid = n.get("nutrientId")
            if nid in NUTRIENT_IDS:
                nutrients[NUTRIENT_IDS[nid]] = round(float(n.get("value", 0) or 0), 2)
        return nutrients

    except Exception:
        return None


def compute_score(row: dict) -> float:
    score = sum(
        min(float(row.get(k, 0) or 0) / NORM_MAX[k], 1.0) * w
        for k, w in WEIGHTS.items()
    )
    return round(score, 5)


def generate_js(items: list[dict], output_path: str):
    from datetime import datetime
    lines = [
        "// NutriMax Grocery Dataset — Kroger API + USDA Nutrition",
        f"// Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"// Items: {len(items)}",
        "const GROCERY_DATA = [",
    ]
    for item in items:
        lines.append(
            f'  {{ id:{item["id"]}, name:"{str(item["name"]).replace(chr(34), chr(39))[:55]}", '
            f'price:{item["price_usd"]}, '
            f'cal:{item.get("cal",0)}, protein:{item.get("protein_g",0)}, '
            f'fiber:{item.get("fiber_g",0)}, '
            f'vitC:{item.get("vitC_mg",0)}, vitA:{item.get("vitA_mcg",0)}, '
            f'category:"{item["category"]}", size:"{item.get("size","")}" }},'
        )
    lines += ["];", "\nexport default GROCERY_DATA;"]
    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Enrich Kroger data with USDA nutrition")
    parser.add_argument("--kroger",   default="kroger_grocery.csv",        help="Kroger CSV from pipeline")
    parser.add_argument("--usda-key", default=os.environ.get("USDA_API_KEY","DEMO_KEY"), help="USDA FDC API key")
    parser.add_argument("--output",   default="grocery_data_enriched.js",  help="Output JS file")
    args = parser.parse_args()

    if not os.path.exists(args.kroger):
        print(f"ERROR: {args.kroger} not found. Run kroger_pipeline.py first.")
        sys.exit(1)

    df = pd.read_csv(args.kroger)
    print(f"Loaded {len(df)} Kroger products")
    print(f"Items missing nutrition: {(df['cal'] == 0).sum()}")
    print(f"\nEnriching via USDA FDC API...")

    enriched = 0
    for idx, row in df.iterrows():
        # Skip if already has nutrition
        if float(row.get("cal", 0) or 0) > 0:
            continue

        name = str(row["name"])
        print(f"  [{idx+1}/{len(df)}] {name[:45]}...", end=" ", flush=True)

        nutrients = usda_search(args.usda_key, name)
        if nutrients:
            for col, val in nutrients.items():
                df.at[idx, col] = val
            enriched += 1
            print(f"✓ cal={nutrients.get('cal',0)}, protein={nutrients.get('protein_g',0)}g")
        else:
            print("— no match")

        time.sleep(0.25)  # rate limit

    # Recompute scores
    df["nutrition_score"] = df.apply(lambda r: compute_score(r.to_dict()), axis=1)
    df = df.sort_values("nutrition_score", ascending=False).reset_index(drop=True)
    df["id"] = df.index + 1

    # Save enriched CSV
    enriched_csv = args.kroger.replace(".csv", "_enriched.csv")
    df.to_csv(enriched_csv, index=False)
    print(f"\n✅ Saved enriched CSV: {enriched_csv}")

    generate_js(df.to_dict(orient="records"), args.output)
    print(f"✅ Saved JS: {args.output}")

    print(f"\nSummary:")
    print(f"  Items enriched with USDA nutrition: {enriched}")
    print(f"  Items still missing nutrition:      {(df['cal']==0).sum()}")
    print(f"  Top scorer: {df.iloc[0]['name']} (score={df.iloc[0]['nutrition_score']:.4f})")


if __name__ == "__main__":
    main()
