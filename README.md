# ASTraM — Bengaluru Traffic Police Command System
### Event-Driven Congestion Intelligence & Dispatch Engine

The ASTraM Command Center is an operational decision support system built for **Bengaluru Traffic Police (BTP)** to manage large-scale crowd events, IPL cricket matches, rallies, and environmental emergencies.

## Live Deployment

The system is deployed and accessible at:  
[https://gridlock-traffic-demand.vercel.app](https://gridlock-traffic-demand.vercel.app)

---

## Core Features

### 1. 2D & 3D Interactive Tactical Mapping
* **2D Spatial Demand Engine**: Dynamic Leaflet map displaying junction impact radiuses, congestion severities, and venue locations across 10 BTP traffic zones.
* **3D WebGL Tactical Mode (Beta)**: Three.js WebGL model of M. Chinnaswamy Stadium, featuring floating 3D venue signboards, gate entrances (Gate 1, 2, 12, 18), pedestrian crowd swarms, animated traffic vehicles, and on-duty police constable positions.

### 2. Automated Special Bandobast Orders
* Generates official Bandobast Deployment Orders specifying exact constable staffing requirements, barricade engineering guidelines (Type-A, Type-B), and signal override timings.
* Recommends smart traffic diversion routes to reduce commuter delay.

### 3. Constable WhatsApp Dispatch Simulator
* Formats low-bandwidth, copy-paste ready WhatsApp Alert Messages for instant broadcast to division traffic officers.
* Includes an interactive dispatch simulator with delivery status indicators.

### 4. Flipkart Last-Mile Logistics Impact
* Quantifies last-mile delivery SLA disruptions and financial risk.
* Assists logistics hubs in pre-positioning delivery fleets before peak congestion windows.

### 5. Economic Cost of Inaction Model
* Calculates commuter time value, fuel wastage, and emergency response delay costs.
* Measures environmental impact by modeling excess CO₂ emissions from idling vehicles.

---

## Local Development

To run the application locally:

```bash
# Clone the repository
git clone https://github.com/rajdeepchatale/gridlock-traffic-demand.git
cd gridlock-traffic-demand

# Install Python dependencies
pip install -r requirements.txt

# Start the Flask development server
python3 app.py
```
