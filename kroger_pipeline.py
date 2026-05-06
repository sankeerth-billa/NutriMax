"""
NutriMax — Kroger API Data Pipeline (FIXED)
============================================
Run:
  python kroger_pipeline.py --client-id YOUR_ID --client-secret YOUR_SECRET --zip 20740
"""

import os, sys, json, time, base64, argparse, requests, pandas as pd
from datetime import datetime

KROGER_BASE   = "https://api.kroger.com/v1"
TOKEN_URL     = f"{KROGER_BASE}/connect/oauth2/token"
PRODUCTS_URL  = f"{KROGER_BASE}/products"
LOCATIONS_URL = f"{KROGER_BASE}/locations"

SEARCH_TERMS = [
    ("whole milk gallon",       "Dairy",     3),
    ("large eggs",              "Dairy",     3),
    ("greek yogurt",            "Dairy",     3),
    ("cheddar cheese",          "Dairy",     2),
    ("butter unsalted",         "Dairy",     2),
    ("cottage cheese",          "Dairy",     2),
    ("chicken breast",          "Protein",   3),
    ("ground beef",             "Protein",   3),
    ("canned tuna",             "Protein",   3),
    ("canned salmon",           "Protein",   2),
    ("peanut butter",           "Protein",   3),
    ("turkey breast",           "Protein",   2),
    ("black beans canned",      "Legumes",   3),
    ("kidney beans canned",     "Legumes",   2),
    ("chickpeas canned",        "Legumes",   2),
    ("lentils dry",             "Legumes",   2),
    ("tofu firm",               "Legumes",   2),
    ("brown rice",              "Grains",    3),
    ("rolled oats",             "Grains",    3),
    ("whole wheat bread",       "Grains",    3),
    ("pasta spaghetti",         "Grains",    2),
    ("quinoa",                  "Grains",    2),
    ("whole grain cereal",      "Grains",    2),
    ("fresh spinach bag",       "Produce",   3),
    ("broccoli crown",          "Produce",   2),
    ("carrots bag",             "Produce",   2),
    ("bananas",                 "Produce",   2),
    ("apples bag",              "Produce",   2),
    ("sweet potatoes",          "Produce",   2),
    ("kale",                    "Produce",   2),
    ("blueberries",             "Produce",   2),
    ("frozen peas",             "Frozen",    2),
    ("frozen broccoli",         "Frozen",    2),
    ("frozen mixed vegetables", "Frozen",    2),
    ("frozen salmon",           "Frozen",    2),
    ("frozen edamame",          "Frozen",    2),
    ("canned tomatoes diced",   "Canned",    2),
    ("canned corn",             "Canned",    2),
    ("tomato sauce canned",     "Canned",    2),
    ("olive oil",               "Pantry",    2),
    ("almonds",                 "Pantry",    2),
    ("walnuts",                 "Pantry",    2),
    ("orange juice",            "Beverages", 2),
    ("almond milk",             "Beverages", 2),
]

WEIGHTS  = {"protein_g": 0.40, "fiber_g": 0.25, "cal": 0.20, "vitC_mg": 0.08, "vitA_mcg": 0.07}
NORM_MAX = {"protein_g": 30.0, "fiber_g": 15.0, "cal": 400.0, "vitC_mg": 90.0, "vitA_mcg": 900.0}

CHAINS_TO_TRY = [
    "KROGER", "HARRIS TEETER", "FRED MEYER", "KING SOOPERS",
    "RALPHS", "SMITHS", "FRYS", "PICK N SAVE", "MARIANOS",
    "CITY MARKET", "DILLONS", "FOOD4LESS",
]

FALLBACK_LOCATIONS = [
    ("70100172", "Kroger - Atlanta, GA"),
    ("01400943", "Kroger - Columbus, OH"),
    ("62000015", "Kroger - Houston, TX"),
    ("02600388", "Kroger - Cincinnati, OH"),
]


def get_access_token(client_id, client_secret):
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(TOKEN_URL,
        headers={"Authorization": f"Basic {credentials}",
                 "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials", "scope": "product.compact"},
        timeout=15)
    if resp.status_code != 200:
        print(f"\nAuth failed ({resp.status_code}): {resp.text[:300]}")
        sys.exit(1)
    print("Authenticated with Kroger API")
    return resp.json()["access_token"]


def get_location_id(token, zip_code):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    for chain in CHAINS_TO_TRY:
        try:
            resp = requests.get(LOCATIONS_URL, headers=headers,
                params={"filter.zipCode.near": zip_code, "filter.limit": 5,
                        "filter.chain": chain}, timeout=15)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                if data:
                    loc  = data[0]
                    lid  = loc["locationId"]
                    name = loc.get("name", chain)
                    city = loc.get("address", {}).get("city", "")
                    print(f"Found store: {name} in {city} (ID: {lid})")
                    return lid
        except Exception:
            pass

    # Try without chain filter
    print(f"  No chain store found near {zip_code}, searching radius 50 miles...")
    try:
        resp = requests.get(LOCATIONS_URL, headers=headers,
            params={"filter.zipCode.near": zip_code, "filter.limit": 1,
                    "filter.radiusInMiles": 50}, timeout=15)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            if data:
                lid = data[0]["locationId"]
                print(f"Found store ID: {lid}")
                return lid
    except Exception:
        pass

    lid, name = FALLBACK_LOCATIONS[0]
    print(f"  Using fallback store: {name} (prices from that region)")
    return lid


def fetch_products(token, location_id, term, limit):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    params  = {"filter.term": term, "filter.limit": limit}
    if location_id:
        params["filter.locationId"] = location_id

    for attempt in range(3):
        try:
            resp = requests.get(PRODUCTS_URL, headers=headers, params=params, timeout=15)
            if resp.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            if resp.status_code == 503:
                time.sleep(3)
                continue
            if resp.status_code != 200:
                return []
            return resp.json().get("data", [])
        except Exception:
            time.sleep(2)
    return []


def parse_product(product, category):
    name  = product.get("description", "")
    brand = product.get("brand", "")
    if not name:
        return None

    price, size = None, ""
    items = product.get("items", [])
    if items:
        price_obj = items[0].get("price", {})
        price = price_obj.get("promo") or price_obj.get("regular")
        size  = items[0].get("size", "")

    if not price or float(price) <= 0:
        return None

    nutrition = product.get("nutrition", {})
    cal     = float(nutrition.get("calories",            0) or 0)
    protein = float(nutrition.get("protein",              0) or 0)
    fiber   = float(nutrition.get("dietaryFiber",         0) or 0)
    fat     = float(nutrition.get("totalFat",             0) or 0)
    carbs   = float(nutrition.get("totalCarbohydrate",    0) or 0)
    vitC = vitA = 0.0
    for vit in nutrition.get("vitamins", []):
        vname = (vit.get("name") or "").lower()
        pct   = float(vit.get("dvPercent") or 0)
        if "vitamin c" in vname:
            vitC = round(pct * 0.9, 1)
        elif "vitamin a" in vname:
            vitA = round(pct * 9.0, 1)

    display = f"{brand} {name}".strip() if brand and brand.lower() not in name.lower() else name
    return {
        "product_id": product.get("productId",""),
        "upc":        product.get("upc",""),
        "name":       display,
        "brand":      brand,
        "category":   category,
        "price_usd":  round(float(price), 2),
        "size":       size,
        "cal":        round(cal, 1),
        "protein_g":  round(protein, 1),
        "fiber_g":    round(fiber, 1),
        "fat_g":      round(fat, 1),
        "carbs_g":    round(carbs, 1),
        "vitC_mg":    round(vitC, 1),
        "vitA_mcg":   round(vitA, 1),
    }


def compute_score(row):
    return round(sum(
        min(float(row.get(k,0) or 0) / NORM_MAX[k], 1.0) * w
        for k,w in WEIGHTS.items()
    ), 5)


def generate_js(items, path):
    lines = [
        "// NutriMax Grocery Dataset — Kroger API",
        f"// Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"// Items: {len(items)}",
        "const GROCERY_DATA = [",
    ]
    for item in items:
        name = str(item.get("name","")).replace('"',"'")[:55]
        size = str(item.get("size","")).replace('"',"'")
        lines.append(
            f'  {{ id:{item["id"]}, name:"{name}", price:{item["price_usd"]}, '
            f'cal:{item["cal"]}, protein:{item["protein_g"]}, fiber:{item["fiber_g"]}, '
            f'vitC:{item["vitC_mg"]}, vitA:{item["vitA_mcg"]}, '
            f'category:"{item["category"]}", size:"{size}" }},'
        )
    lines += ["];", "\nexport default GROCERY_DATA;"]
    with open(path, "w") as f:
        f.write("\n".join(lines))


def generate_report(df, zip_code):
    lines = [
        "NutriMax Kroger Dataset Report",
        "=" * 50,
        f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"ZIP code  : {zip_code}",
        f"Total items    : {len(df)}",
        f"With prices    : {(df['price_usd'] > 0).sum()}",
        f"With nutrition : {(df['cal'] > 0).sum()}",
        f"Price range    : ${df['price_usd'].min():.2f} - ${df['price_usd'].max():.2f}",
        f"Avg price      : ${df['price_usd'].mean():.2f}",
        "", "BY CATEGORY",
    ]
    for cat, cnt in df["category"].value_counts().items():
        lines.append(f"  {cat:<15} {cnt} items")
    lines += ["", "TOP 15 BY NUTRITION SCORE"]
    for _, r in df.nlargest(15, "nutrition_score").iterrows():
        lines.append(f"  {str(r['name'])[:40]:<41} score={r['nutrition_score']:.4f}  ${r['price_usd']:.2f}")
    with open("kroger_dataset_report.txt", "w") as f:
        f.write("\n".join(lines))
    print("Wrote kroger_dataset_report.txt")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id",     default=None)
    parser.add_argument("--client-secret", default=None)
    parser.add_argument("--zip",           default="10001")
    parser.add_argument("--output-js",     default="grocery_data.js")
    parser.add_argument("--output-csv",    default="kroger_grocery.csv")
    args = parser.parse_args()

    client_id     = args.client_id     or os.environ.get("KROGER_CLIENT_ID")
    client_secret = args.client_secret or os.environ.get("KROGER_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("ERROR: Provide --client-id and --client-secret")
        sys.exit(1)

    print("=" * 60)
    print("NutriMax — Kroger API Data Pipeline")
    print("=" * 60)

    token       = get_access_token(client_id, client_secret)
    location_id = get_location_id(token, args.zip)

    print(f"\nFetching {len(SEARCH_TERMS)} product categories...")
    all_records, seen_upcs = [], set()

    for i, (term, category, limit) in enumerate(SEARCH_TERMS):
        print(f"  [{i+1:02d}/{len(SEARCH_TERMS)}] {term}...", end=" ", flush=True)
        products = fetch_products(token, location_id, term, limit)
        added = 0
        for p in products:
            parsed = parse_product(p, category)
            if not parsed:
                continue
            upc = parsed["upc"]
            if upc and upc in seen_upcs:
                continue
            if upc:
                seen_upcs.add(upc)
            all_records.append(parsed)
            added += 1
        print(f"{added} added  (total: {len(all_records)})")
        time.sleep(0.4)

    if not all_records:
        print("\nNo products returned. Try a different ZIP code:")
        print("  python kroger_pipeline.py --client-id ... --client-secret ... --zip 30301")
        print("  Other good ZIPs: 43201 (Columbus OH), 77001 (Houston TX), 60601 (Chicago IL)")
        sys.exit(1)

    df = pd.DataFrame(all_records)
    for col in ["cal","protein_g","fiber_g","fat_g","carbs_g","vitC_mg","vitA_mcg"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["nutrition_score"] = df.apply(lambda r: compute_score(r.to_dict()), axis=1)
    df = df.sort_values("nutrition_score", ascending=False).reset_index(drop=True)
    df["id"] = df.index + 1

    df.to_csv(args.output_csv, index=False)
    print(f"\nSaved {args.output_csv}  ({len(df)} rows)")

    generate_js(df.to_dict(orient="records"), args.output_js)
    print(f"Saved {args.output_js}  ({len(df)} items)")

    generate_report(df, args.zip)

    print(f"\n{'='*60}")
    print(f"DONE — {len(df)} products fetched")
    print(f"  With prices    : {(df['price_usd']>0).sum()}")
    print(f"  With nutrition : {(df['cal']>0).sum()}")
    print(f"\nNext step: paste grocery_data.js into nutrimax.jsx")

    if (df["cal"] == 0).all():
        print(f"\nNOTE: Nutrition data not returned by Kroger API for this location.")
        print(f"Run the USDA enrichment script to fill it in:")
        print(f"  python kroger_enrich_nutrition.py --kroger {args.output_csv} --usda-key YOUR_USDA_KEY")
        print(f"  (Get free USDA key at: https://fdc.nal.usda.gov/api-guide.html)")

if __name__ == "__main__":
    main()
