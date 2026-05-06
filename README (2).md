# NutriMax 🥦
### Budget-Aware Grocery Optimizer
**MSML606 — Extra Credit Project 2**

NutriMax solves the real-world problem of maximizing nutritional value within a fixed grocery budget using the **0/1 Knapsack Dynamic Programming algorithm**. Given a budget, it finds the optimal combination of grocery items that maximizes a composite nutrition score across calories, protein, fiber, and key vitamins.

---

## Live Demo
Run locally following the setup steps below.

---

## How It Works

### Algorithm — 0/1 Knapsack (Dynamic Programming)
- Each grocery item is either purchased (1) or not (0) — no partial purchases
- Budget = knapsack capacity, prices = weights, nutrition scores = values
- DP recurrence: `dp[i][b] = max(dp[i-1][b], dp[i-1][b - p[i]] + v[i])`
- Time complexity: **O(N × B)** | Space: **O(N × B)**
- Traceback through DP table recovers the selected items

### Nutrition Score Formula
```
score = 0.40 × norm(protein)
      + 0.25 × norm(fiber)
      + 0.20 × norm(calories)
      + 0.08 × norm(vitamin_c)
      + 0.07 × norm(vitamin_a)

norm(x) = min(x / MAX_x, 1.0)
```

### Dataset
- **98 real grocery products** fetched from the **Kroger Public API**
- **Real retail prices** from local Kroger/Harris Teeter stores
- **Nutrition data** enriched via **USDA FoodData Central API**
- 10 categories: Dairy, Protein, Legumes, Grains, Produce, Frozen, Canned, Pantry, Snacks, Beverages

---

## Features
- 🛒 **Optimizer Tab** — set your budget, click optimize, get your shopping list
- 📊 **DP Visualizer Tab** — step-by-step animated DP table
- 📄 **Report Tab** — full written project report
- ⚙️ **Configurable weights** — adjust nutrition priorities in real time
- 📈 **Spending breakdown** by category

---

## Setup Guide

### Prerequisites
- Python 3.8+
- Node.js LTS → https://nodejs.org
- Git → https://git-scm.com

---

### Step 1 — Clone the Repository
```powershell
git clone https://github.com/sankeerth-billa/NutriMax.git
cd NutriMax
```

---

### Step 2 — Run the React App

```powershell
npm create vite@latest nutrimax-app -- --template react
```
Hit **Enter** for all questions, then:

```powershell
copy "nutrimax.jsx" "nutrimax-app\src\App.jsx"
cd nutrimax-app
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

---

### Step 3 — (Optional) Re-fetch Kroger Data

Only needed if you want fresh grocery prices from Kroger.

**Install Python dependencies:**
```powershell
pip install requests pandas thefuzz python-Levenshtein
```

**Get free Kroger API credentials:**
1. Go to https://developer.kroger.com/
2. Register App → select **Product API** → **Production**
3. Copy your Client ID and Client Secret

**Run the pipeline:**
```powershell
python kroger_pipeline.py --client-id YOUR_ID --client-secret YOUR_SECRET --zip YOUR_ZIPCODE
```

**Enrich with nutrition data:**

Get a free USDA API key at https://api.data.gov/signup/ then run:
```powershell
python kroger_enrich_nutrition.py --kroger kroger_grocery.csv --usda-key YOUR_USDA_KEY
```

---

## Project Files

| File | Description |
|------|-------------|
| `nutrimax.jsx` | Main React app (Optimizer + DP Visualizer + Report) |
| `kroger_pipeline.py` | Fetches real Kroger products and prices |
| `kroger_enrich_nutrition.py` | Enriches products with USDA nutrition data |
| `kroger_grocery.csv` | Raw Kroger dataset |
| `kroger_grocery_enriched.csv` | Dataset with nutrition filled in |
| `kroger_dataset_report.txt` | Dataset summary statistics |
| `requirements.txt` | Python dependencies |

---

## Requirements

### Python
```
requests
pandas
thefuzz
python-Levenshtein
anthropic
```

### Node.js
```
vite
react
react-dom
```

---

## Data Sources
- **Kroger Public API** — https://developer.kroger.com (real products + prices)
- **USDA FoodData Central** — https://fdc.nal.usda.gov (nutrition data)
- **USDA Economic Research Service** — https://www.ers.usda.gov (price reference)

---

## References
1. USDA FoodData Central — https://fdc.nal.usda.gov
2. Kroger Developer API — https://developer.kroger.com
3. Cormen et al. Introduction to Algorithms (CLRS), 4th ed. MIT Press, 2022. Chapter 16
4. Kellerer, Pferschy, Pisinger. Knapsack Problems. Springer, 2004

---

## Team
| Name | Role |
|------|------|
| Prathamesh Uravane | Algorithm Design, Data Pipeline |
| Sankeerth Billa | Frontend Development, Data Enrichment |

**Course:** MSML606 — Extra Credit Project 2
