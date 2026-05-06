# NutriMax — Kroger API Pipeline
## MSML606 Extra Credit Project 2

---

## What This Does

Fetches **real grocery products with live prices** from Kroger's public API,
then generates a dataset ready to plug into the NutriMax optimizer.

```
Kroger Public API (real products + real prices)
           ↓
  kroger_pipeline.py        →  kroger_grocery.csv
                                grocery_data.js  ← plug into nutrimax.jsx
                                kroger_dataset_report.txt
           ↓ (if nutrition missing)
  kroger_enrich_nutrition.py → grocery_data_enriched.js  (USDA nutrition matched)
```

---

## Step 0 — Get Your FREE Kroger API Credentials

1. Go to **https://developer.kroger.com/**
2. Click **"Register App"** (free, takes 2 minutes)
3. Fill in:
   - App Name: `NutriMax`
   - Redirect URI: `http://localhost:8000`
4. Copy your **Client ID** and **Client Secret**

---

## Step 1 — Install & Run

```bash
pip install requests pandas

# Set credentials as environment variables
export KROGER_CLIENT_ID=your_client_id_here
export KROGER_CLIENT_SECRET=your_client_secret_here

# Run with your ZIP code (uses local Kroger store prices)
python kroger_pipeline.py --zip 48201

# Or pass credentials directly
python kroger_pipeline.py --client-id YOUR_ID --client-secret YOUR_SECRET --zip 10001
```

**Output files:**
| File | Description |
|------|-------------|
| `kroger_grocery.csv` | All fetched products with prices |
| `grocery_data.js` | Drop into `nutrimax.jsx` |
| `kroger_dataset_report.txt` | Stats for project report |

---

## Step 2 (Optional) — Enrich Nutrition Data

The Kroger public API sometimes omits nutrition facts (calories, protein, fiber).
If many items show 0, run the enrichment script which fuzzy-matches product names
to USDA FoodData Central:

```bash
pip install thefuzz python-Levenshtein

# Get free USDA key at: https://fdc.nal.usda.gov/api-guide.html
export USDA_API_KEY=your_usda_key

python kroger_enrich_nutrition.py \
  --kroger kroger_grocery.csv \
  --usda-key $USDA_API_KEY \
  --output grocery_data_enriched.js
```

**Output:** `grocery_data_enriched.js` — use this instead of `grocery_data.js`

---

## Step 3 — Plug Into the App

In `nutrimax.jsx`, find the `GROCERY_DATA` array and replace it with the
contents of `grocery_data.js` (or `grocery_data_enriched.js`).

---

## What Kroger API Returns

```json
{
  "productId": "0001111041700",
  "upc": "0001111041700",
  "description": "Kroger Whole Milk",
  "brand": "Kroger",
  "items": [
    {
      "price": { "regular": 3.49, "promo": null },
      "size": "1 gal",
      "soldBy": "UNIT"
    }
  ],
  "nutrition": {
    "calories": 150,
    "protein": 8,
    "dietaryFiber": 0,
    "totalFat": 8,
    "vitamins": [
      { "name": "Vitamin D", "dvPercent": 15 },
      { "name": "Vitamin A", "dvPercent": 6 }
    ]
  }
}
```

---

## Nutrition Score Formula

```
score = 0.40 × norm(protein)
      + 0.25 × norm(fiber)
      + 0.20 × norm(calories)
      + 0.08 × norm(vitamin_c)
      + 0.07 × norm(vitamin_a)

norm(x) = min(x / MAX_x, 1.0)
```

---

## API Rate Limits

Kroger's public API allows ~10,000 requests/day (more than enough).
The pipeline adds 0.3s sleep between requests to be safe.

---

## Project Files

```
nutrimax/
├── nutrimax.jsx                  ← Main React app
├── kroger_pipeline.py            ← Main data pipeline (THIS)
├── kroger_enrich_nutrition.py    ← Optional USDA nutrition enricher
├── README_kroger.md              ← This file
├── kroger_grocery.csv            ← (generated)
├── grocery_data.js               ← (generated, plug into app)
├── grocery_data_enriched.js      ← (generated if enrichment run)
└── kroger_dataset_report.txt     ← (generated)
```

---

## Team
- Prathamesh Uravane
- Sankeerth Billa

**Course:** MSML606 — Extra Credit Project 2
