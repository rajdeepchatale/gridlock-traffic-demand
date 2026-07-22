# ASTraM — Upgrades, Missing Features & Roadmap

> **Document Purpose:** Complete backlog and architectural roadmap for future coding sessions. Outlines missing domain logic, 3D WebGL visualizer enhancements, ML pipeline improvements, and logistics features for **Gridlock Hackathon 2.0**.

---

## 1. 🎨 3D WebGL Tactical Mode Upgrades (Three.js Engine)

### 🚌 A. Dynamic Team Buses & Event Assets
- [ ] **Season & Match-Specific Team Buses**:
  - **April/May (Peak IPL)**: Render branded 3D team buses (e.g., RCB Red/Gold team bus vs. CSK Yellow team bus) parked near Gate 1 & Gate 18 VIP entryways.
  - **July / Off-Season**: Remove IPL team buses; replace with standard BMTC Volvo city buses or domestic team vehicles.
- [ ] **Dynamic 3D Crowd & Vehicle Densities**:
  - Scale pedestrian particle swarm count in 3D based on event crowd size (e.g., 34,000 IPL crowd = dense 3D swarms vs. 11,900 off-season crowd = sparse swarms).
- [ ] **Weather & Environment Shaders**:
  - **Monsoon Mode (June–August)**: Add animated 3D rain particle effects, wet asphalt road surface reflection shaders, and cloudy atmospheric lighting.
  - **Night Match Mode**: Toggle stadium floodlights and vehicle headlight beam trails for evening matches (7:30 PM).

### 📍 B. Interactive 3D Gate & Constable Controls
- [ ] **Clickable 3D Gate Signboards**:
  - Make Gate 1, Gate 2, Gate 12, and Gate 18 3D Floating Badges clickable to inspect gate-specific pedestrian queue times and entrance congestion.
- [ ] **Constable Deployment Mesh Pins**:
  - Render 3D constable figure pins at assigned junction posts.
  - Toggle between **Before Deployment** (missing constables) and **After Deployment** (constables positioned at key barricades).

---

## 2. 🧠 Event, Calendar & Weather Domain Logic

- [ ] **IPL & Event Fixture Schedule Integration**:
  - Integrate a structured calendar mapping real match fixtures (e.g., *RCB vs. CSK*, *RCB vs. MI*) for April/May dates.
  - Show team logos and match names instead of generic "IPL Match".
- [ ] **Live Weather & Monsoon API**:
  - Integrate Open-Meteo or IMD weather API to automatically fetch live/forecasted Bengaluru rainfall (mm/hr) and dynamically trigger monsoon delay multipliers.
- [ ] **Public Transit & BMTC Shuttle Factors**:
  - Incorporate Namma Metro (MG Road & Cubbon Park stations) capacity and BMTC event shuttle buses to model how public transit reduces private vehicle surges.

---

## 3. 📦 Flipkart Last-Mile Logistics Impact Engine

- [ ] **Hub-Specific Delivery Risk Mapping**:
  - Map specific Flipkart hub locations (Koramangala Hub, Indiranagar Hub, Central Delivery Hub) on the 2D/3D map.
  - Calculate real-time ETA delay multipliers for delivery routes originating from each hub.
- [ ] **Automated Fleet Dispatch & Pre-Positioning Recommendations**:
  - Generate time-window recommendations for hub managers:  
    *Example: "Dispatch 85% of Central Hub orders before 5:15 PM to avoid Gate 1 & MG Road surge."*
- [ ] **Financial SLA Loss Estimator**:
  - Estimate potential penalty costs from breached 10-min / 30-min quick-commerce SLAs during event peak hours.

---

## 4. 📋 Traffic Police Bandobast & Dispatch Enhancements

- [ ] **Dual-Language WhatsApp Alerts (Kannada + English)**:
  - Add a toggle for low-bandwidth WhatsApp officer briefs in both **English** and **Kannada** (Karnataka official language for BTP ground constables).
- [ ] **One-Click Official PDF Export**:
  - Add a "Export Official Deployment Order" button generating a clean PDF formatted with official BTP headers, constable staffing tables, barricading Type-A/B diagrams, and sign-off signature blocks.
- [ ] **Signal Timing Override Calculator**:
  - Calculate exact recommended green-light extension seconds (e.g., *"Extend Cubbon Road green phase by +45s between 22:00 and 23:15"*).

---

## 5. 📊 ML Model & Data Pipeline Enhancements

- [ ] **Real-Time Traffic Camera / Sensors Feed Integration**:
  - Add a mock/live data ingestion pipe for Bengaluru Traffic Police camera traffic count sensors.
- [ ] **Spatial Heatmap Smoothing**:
  - Implement Kriging or Inverse Distance Weighting (IDW) spatial interpolation for continuous 2D Leaflet congestion heatmaps.
- [ ] **Historical Baseline Comparison**:
  - Compare predicted event congestion against typical non-event day traffic baselines for the exact same day of the week.

---

## 🚀 Quick Execution Priority for Next Coding Session

1. **Priority 1**: Dynamic 3D Vehicles (RCB/CSK team buses in April/May vs. city buses in July) & rain shaders in Three.js (`static/js/app.js`).
2. **Priority 2**: Flipkart Hub specific delivery route delay calculators & pre-positioning recommendation cards.
3. **Priority 3**: Kannada + English dual-language WhatsApp dispatch text formatter.
4. **Priority 4**: PDF Bandobast order exporter.
