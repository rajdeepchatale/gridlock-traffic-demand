# ASTraM — Bengaluru Traffic Police Command System
### Event-Driven Congestion Intelligence & Dispatch Engine · Gridlock Hackathon 2.0

ASTraM is an operational decision-support system for **Bengaluru Traffic Police (BTP)** that turns a
planned event — an IPL match, a political rally, a festival, a flooding alert — into a concrete,
field-ready traffic plan: which junctions will choke, when, how many constables to post where, which
diversions to open, and what inaction would cost the city.

The repository holds two connected pieces:

| Part | What it does | Entry point |
|---|---|---|
| **Command Center** | Flask API + browser dashboard that predicts event impact and generates bandobast orders | [`app.py`](app.py), [`engine/`](engine/) |
| **Demand Forecasting Pipeline** | Gradient-boosted ensemble that forecasts geohash-level traffic demand from the hackathon dataset | [`solution.py`](solution.py) |

## Live Deployment

**[https://gridlock-traffic-demand.vercel.app](https://gridlock-traffic-demand.vercel.app)**

---

## Core Features

### 1. 2D & 3D Interactive Tactical Mapping
* **2D Spatial Demand Engine** — Leaflet map rendering junction impact radiuses, congestion severity, and venue locations across 10 BTP traffic zones.
* **3D WebGL Tactical Mode (Beta)** — Three.js model of M. Chinnaswamy Stadium with floating venue signboards, gate entrances (Gates 1, 2, 12, 18), pedestrian crowd swarms, animated vehicles, and on-duty constable positions.

### 2. Automated Special Bandobast Orders
* Generates deployment orders specifying constable staffing, barricade engineering guidelines (Type-A / Type-B), and signal override timings.
* Recommends diversion routes to cut commuter delay, broken down by zone and shift window.

### 3. Constable WhatsApp Dispatch Simulator
* Formats low-bandwidth, copy-paste-ready alert messages for broadcast to division traffic officers.
* Interactive dispatch simulator with delivery status indicators.

### 4. Flipkart Last-Mile Logistics Impact
* Quantifies last-mile delivery SLA disruption and the financial risk attached to it.
* Helps logistics hubs pre-position fleets ahead of peak congestion windows.

### 5. Economic Cost of Inaction Model
* Prices commuter time, fuel wastage, and emergency-response delay with and without deployment.
* Models excess CO₂ emissions from idling vehicles.

---

## Prediction Engine

The [`engine/`](engine/) package is the domain core. It is deterministic and dependency-light — no
model artifacts to ship, no external API calls at request time.

| Module | Responsibility |
|---|---|
| [`bengaluru_kb.py`](engine/bengaluru_kb.py) | Knowledge base: **28 junctions**, **10 venues**, **8 event types**, **10 BTP zones**, plus economic constants |
| [`impact_predictor.py`](engine/impact_predictor.py) | Spatial-temporal congestion propagation — distance decay, hourly load profile, BPR delay function against junction capacity, seasonality (IPL off-season scaling, monsoon delay factors) |
| [`deployment_generator.py`](engine/deployment_generator.py) | Bandobast order: shift windows, constable assignments, barricades, signal overrides, diversions, WhatsApp alert |
| [`cost_analyzer.py`](engine/cost_analyzer.py) | With/without-deployment cost comparison, savings, and deployment ROI |

Each junction carries real coordinates, base capacity (vehicles/hr), normal-day constable strength,
road type, and zone, so impact is scored against actual road capacity rather than a generic index.

**Modelled event types:** IPL match · political rally · religious festival · concert · exhibition ·
rain flooding · construction · VIP movement.

---

## Demand Forecasting Pipeline

[`solution.py`](solution.py) is the Gridlock 2.0 competition pipeline. It trains directly on the
`demand` target (no scaling noise) and blends three gradient-boosting engines.

**Data** — [`dataset/`](dataset/): 77,299 training rows and 41,778 test rows keyed by
`geohash`, `day`, and `timestamp`, with `RoadType`, `NumberofLanes`, `LargeVehicles`, `Landmarks`,
`Temperature`, and `Weather` as covariates. Target `demand` is normalised to `[0, 1]`; scoring is R².

**Feature engineering** (`run_feature_engineering`):
* `geohash_hour_mean` — historical demand at the same geohash and hour on the previous day
* `early_morning_mean` — location-specific morning baseline for the current day, separating weekday from weekend profiles
* `geohash_target_enc` — out-of-fold target encoding over geohashes
* Geohash prefix groupings (2/3/4-char) so tree models can pool nearby locations
* Proximity to Bengaluru hotspots — Majestic, Whitefield, Electronic City, Manyata
* Inline base32 geohash decoding to lat/lon — no geospatial dependency required

**Modelling** (`train_and_predict`): LightGBM, XGBoost, and CatBoost trained under K-fold CV, then
blended with SciPy `SLSQP`-optimised linear weights (5-fold, `random_state=42`). Each booster is imported lazily and skipped if
unavailable, so the pipeline degrades gracefully to whichever engines are installed.

[`post_process.py`](post_process.py) is a small submission utility that rescales baseline
`predictions.csv` demand by fixed multipliers (1.12 / 1.16 / 1.20), clipped to `[0, 1]`.

---

## Repository Layout

```
.
├── app.py                     # Flask server — page + API routes
├── engine/
│   ├── bengaluru_kb.py        # Junctions, venues, event types, zones, economic constants
│   ├── impact_predictor.py    # Spatial-temporal impact model
│   ├── deployment_generator.py# Bandobast order + WhatsApp alert generation
│   └── cost_analyzer.py       # Economic disruption & ROI model
├── templates/index.html       # Command Center dashboard
├── static/
│   ├── css/styles.css
│   └── js/app.js              # Leaflet 2D map + Three.js 3D tactical mode
├── solution.py                # Demand forecasting pipeline (LGBM + XGB + CatBoost blend)
├── post_process.py            # Submission rescaling utility
├── dataset/                   # train.csv, test.csv, sample_submission.csv
├── requirements.txt           # Web app dependencies
├── ARCHITECTURE.md            # System design reference
└── UPGRADES_AND_ROADMAP.md    # Backlog and planned work
```

---

## Local Development

```bash
git clone https://github.com/rajdeepchatale/gridlock-traffic-demand.git
cd gridlock-traffic-demand

pip install -r requirements.txt
python3 app.py
```

The server starts on `http://localhost:5000` (override with the `PORT` environment variable).

### Running the forecasting pipeline

`requirements.txt` covers the web app only. The pipeline needs the ML stack as well:

```bash
pip install scikit-learn scipy lightgbm xgboost catboost
python3 solution.py          # writes predictions.csv
python3 post_process.py      # writes predictions_x1.12/1.16/1.20.csv
```

---

## API

### `POST /api/predict`

Runs the full pipeline: impact prediction → deployment order → economic analysis.

```jsonc
{
  "event_type":     "ipl_match",     // key from EVENT_TYPES
  "venue_id":       "chinnaswamy",   // key from VENUES, or "custom"
  "event_date":     "2026-04-15",
  "event_time":     "19:30",
  "expected_crowd":  34000,          // optional — defaults to venue capacity x event factor x season
  "custom_lat":      12.9788,        // optional — overrides coordinates when venue_id is "custom"
  "custom_lon":      77.5996
}
```

Response:

```jsonc
{
  "success": true,
  "impact":     { "event", "seasonality", "impact_summary", "junction_impacts", "timeline" },
  "deployment": { "order_reference", "generated_at", "event", "shift", "resources",
                  "assignments", "barricade_locations", "signal_overrides",
                  "diversions", "zone_breakdown", "whatsapp_alert" },
  "economics":  { "without_deployment", "with_deployment", "savings", "deployment_investment" }
}
```

Failures return HTTP 400 with `{ "success": false, "error": "..." }`.

### `GET /api/metadata`

Returns the event types, venues, junctions, and zones the UI populates its controls from.

---

## Architecture

[ARCHITECTURE.md](ARCHITECTURE.md) documents the system design — request lifecycle, layer
boundaries, the eight-stage computation model with its BPR delay function and calibration
constants, data contracts, the decoupled ML pipeline, and known gaps.

## Roadmap

Planned work is tracked in [UPGRADES_AND_ROADMAP.md](UPGRADES_AND_ROADMAP.md) — dynamic 3D team
buses and monsoon shaders, IPL fixture and live weather integration, Flipkart hub-level delivery
risk mapping, Kannada/English dual-language dispatch alerts, PDF bandobast export, and spatial
heatmap smoothing.

---

## Note

This is a hackathon prototype built for **Gridlock Hackathon 2.0**. It is not an official Bengaluru
Traffic Police system and is not affiliated with or endorsed by BTP, Flipkart, or any event
organiser. Deployment orders, alerts, and cost figures it generates are illustrative model output,
not operational instructions.
