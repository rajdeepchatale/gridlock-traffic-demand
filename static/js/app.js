/**
 * Gridlock 2.0 — Event-Driven Congestion Command Center
 * Frontend Application Logic
 */

// ─── State ───
let map = null;
let markersLayer = null;
let impactCircle = null;
let currentResult = null;

// ─── Helpers ───
function formatINR(amount) {
    if (amount >= 10000000) return '₹' + (amount / 10000000).toFixed(2) + ' Cr';
    if (amount >= 100000) return '₹' + (amount / 100000).toFixed(2) + ' L';
    if (amount >= 1000) return '₹' + (amount / 1000).toFixed(1) + 'K';
    return '₹' + amount.toLocaleString('en-IN');
}

function formatNumber(n) {
    return n.toLocaleString('en-IN');
}

function scrollToInput() {
    document.getElementById('inputSection').scrollIntoView({ behavior: 'smooth' });
}

// ─── Main Prediction Call ───
async function runPrediction() {
    const btn = document.getElementById('predictBtn');
    const loader = document.getElementById('loadingOverlay');
    const results = document.getElementById('resultsContainer');

    // Gather inputs
    const payload = {
        event_type: document.getElementById('eventType').value,
        venue_id: document.getElementById('venueSelect').value,
        event_date: document.getElementById('eventDate').value,
        event_time: document.getElementById('eventTime').value,
        expected_crowd: document.getElementById('expectedCrowd').value || null,
    };

    // Show loader
    btn.disabled = true;
    loader.classList.add('active');
    results.style.display = 'none';

    try {
        const resp = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await resp.json();

        if (!data.success) {
            alert('Prediction failed: ' + (data.error || 'Unknown error'));
            return;
        }

        currentResult = data;
        results.style.display = 'block';
        renderResults(data);

        // Scroll to results
        setTimeout(() => {
            document.getElementById('summarySection').scrollIntoView({ behavior: 'smooth' });
        }, 300);

    } catch (err) {
        alert('Error connecting to server: ' + err.message);
    } finally {
        btn.disabled = false;
        loader.classList.remove('active');
    }
}

// ─── Render All Results ───
function renderResults(data) {
    renderSummary(data);
    renderMap(data);
    renderTimeline(data);
    renderImpactTable(data);
    renderBandobast(data);
    renderEconomics(data);
    renderFlipkart(data);
    renderWhatsApp(data);
}

// ─── Summary Cards ───
function renderSummary(data) {
    const event = data.impact.event;
    const summary = data.impact.impact_summary;

    document.getElementById('eventBadge').innerHTML =
        `${event.icon} ${event.type_name} — ${event.venue}`;

    const grid = document.getElementById('summaryGrid');
    grid.innerHTML = `
        <div class="summary-card blue">
            <span class="card-icon">👥</span>
            <span class="card-value">${formatNumber(event.expected_crowd)}</span>
            <span class="card-label">Expected Crowd</span>
            <span class="card-sub">${formatNumber(event.vehicles_generated)} vehicles</span>
        </div>
        <div class="summary-card red">
            <span class="card-icon">🚧</span>
            <span class="card-value">${summary.affected_junctions}</span>
            <span class="card-label">Junctions Affected</span>
            <span class="card-sub">${summary.critical_junctions} critical, ${summary.high_junctions} high</span>
        </div>
        <div class="summary-card yellow">
            <span class="card-icon">⏱️</span>
            <span class="card-value">${summary.avg_delay_without_deployment_min} min</span>
            <span class="card-label">Avg Delay (No Deploy)</span>
            <span class="card-sub">Window: ${summary.impact_window_start} — ${summary.impact_window_end}</span>
        </div>
        <div class="summary-card green">
            <span class="card-icon">✅</span>
            <span class="card-value">${summary.avg_delay_with_deployment_min} min</span>
            <span class="card-label">Avg Delay (With Deploy)</span>
            <span class="card-sub">${summary.delay_reduction_pct}% reduction</span>
        </div>
        <div class="summary-card purple">
            <span class="card-icon">👮</span>
            <span class="card-value">${summary.total_extra_constables}</span>
            <span class="card-label">Extra Constables Needed</span>
            <span class="card-sub">Above normal deployment</span>
        </div>
        <div class="summary-card cyan">
            <span class="card-icon">📍</span>
            <span class="card-value">${event.impact_radius_km} km</span>
            <span class="card-label">Impact Radius</span>
            <span class="card-sub">${event.predictability} predictability</span>
        </div>
    `;
}

// ─── Leaflet Map ───
function renderMap(data) {
    const event = data.impact.event;
    const junctions = data.impact.junction_impacts;
    const container = document.getElementById('mapContainer');

    // Initialize or reset map
    if (map) {
        map.remove();
    }

    map = L.map(container, {
        center: [event.venue_lat, event.venue_lon],
        zoom: 13,
        zoomControl: true,
    });

    // Dark tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '© OpenStreetMap contributors © CARTO',
        maxZoom: 18,
    }).addTo(map);

    // Impact radius circle
    L.circle([event.venue_lat, event.venue_lon], {
        radius: event.impact_radius_km * 1000,
        color: 'rgba(59,130,246,0.4)',
        fillColor: 'rgba(59,130,246,0.08)',
        fillOpacity: 0.3,
        weight: 2,
        dashArray: '8 4',
    }).addTo(map);

    // Venue marker
    const venueIcon = L.divIcon({
        className: 'custom-div-icon',
        html: `<div style="
            width:36px;height:36px;
            background:var(--accent-purple,#8b5cf6);
            border-radius:50%;
            border:3px solid white;
            display:flex;align-items:center;justify-content:center;
            font-size:18px;
            box-shadow:0 0 20px rgba(139,92,246,0.6);
        ">${event.icon}</div>`,
        iconSize: [36, 36],
        iconAnchor: [18, 18],
    });

    L.marker([event.venue_lat, event.venue_lon], { icon: venueIcon })
        .addTo(map)
        .bindPopup(`
            <div class="popup-title">${event.venue}</div>
            <div class="popup-detail">${event.type_name}</div>
            <div class="popup-detail">Crowd: ${formatNumber(event.expected_crowd)}</div>
        `);

    // Junction markers
    junctions.forEach(j => {
        const size = j.severity === 'CRITICAL' ? 20 : j.severity === 'HIGH' ? 16 : 12;
        const color = j.color;

        const jIcon = L.divIcon({
            className: 'custom-div-icon',
            html: `<div style="
                width:${size}px;height:${size}px;
                background:${color};
                border-radius:50%;
                border:2px solid rgba(255,255,255,0.7);
                box-shadow:0 0 10px ${color}80;
            "></div>`,
            iconSize: [size, size],
            iconAnchor: [size/2, size/2],
        });

        L.marker([j.lat, j.lon], { icon: jIcon })
            .addTo(map)
            .bindPopup(`
                <div class="popup-title">${j.name}</div>
                <span class="popup-severity" style="background:${color}">${j.severity}</span>
                <div class="popup-detail">Distance: ${j.distance_km} km</div>
                <div class="popup-detail">Delay (no deploy): ${j.delay_without_deployment_min} min</div>
                <div class="popup-detail">Delay (with deploy): ${j.delay_with_deployment_min} min</div>
                <div class="popup-detail">Constables: ${j.total_constables} (${j.extra_constables_needed} extra)</div>
                <div class="popup-detail">Capacity ratio: ${j.capacity_ratio}x</div>
            `);
    });

    // Fit bounds
    const allPoints = [[event.venue_lat, event.venue_lon], ...junctions.map(j => [j.lat, j.lon])];
    if (allPoints.length > 1) {
        map.fitBounds(allPoints, { padding: [40, 40] });
    }

    setTimeout(() => map.invalidateSize(), 200);
}

// ─── Congestion Timeline ───
function renderTimeline(data) {
    const timeline = data.impact.timeline;
    const chart = document.getElementById('timelineChart');
    const maxCongestion = Math.max(...timeline.map(t => t.congestion_level), 1);

    chart.innerHTML = timeline.map(t => {
        const height = Math.max(8, (t.congestion_level / maxCongestion) * 180);
        let color;
        if (t.congestion_level > maxCongestion * 0.8) color = 'var(--severity-critical)';
        else if (t.congestion_level > maxCongestion * 0.5) color = 'var(--severity-high)';
        else if (t.congestion_level > maxCongestion * 0.3) color = 'var(--severity-moderate)';
        else color = 'var(--severity-low)';

        return `
            <div class="timeline-bar-group">
                <div class="timeline-bar" 
                     style="height:${height}px; background:${color};" 
                     title="${t.time} — ${t.phase} (${t.congestion_level}x)">
                </div>
                <span class="timeline-bar-label">${t.time}</span>
                <span class="timeline-bar-phase">${t.phase}</span>
            </div>
        `;
    }).join('');
}

// ─── Impact Table ───
function renderImpactTable(data) {
    const junctions = data.impact.junction_impacts;
    const tbody = document.getElementById('impactTableBody');

    tbody.innerHTML = junctions.map(j => `
        <tr>
            <td><strong>${j.name}</strong></td>
            <td>${j.zone}</td>
            <td>${j.distance_km}</td>
            <td><span class="severity-badge ${j.severity}">${j.severity}</span></td>
            <td>${j.capacity_ratio}x</td>
            <td style="color:var(--accent-red);font-weight:600">${j.delay_without_deployment_min} min</td>
            <td style="color:var(--accent-green);font-weight:600">${j.delay_with_deployment_min} min</td>
            <td><strong>${j.total_constables}</strong> <span style="color:var(--text-muted)">(+${j.extra_constables_needed})</span></td>
        </tr>
    `).join('');
}

// ─── Bandobast Deployment Order ───
function renderBandobast(data) {
    const d = data.deployment;
    const card = document.getElementById('bandobastCard');

    // Filter assignments with severity > LOW
    const activeAssignments = d.assignments.filter(a => a.severity !== 'LOW' || a.extra_constables > 0);

    card.innerHTML = `
        <div class="bandobast-header">
            <h3>⚡ Special Bandobast Order</h3>
            <div class="bandobast-ref">${d.order_reference} | Generated: ${d.generated_at}</div>
        </div>
        <div class="bandobast-meta">
            <div class="bandobast-meta-item">
                <span class="meta-label">Event</span>
                <span class="meta-value">${d.event.icon} ${d.event.type_name}</span>
            </div>
            <div class="bandobast-meta-item">
                <span class="meta-label">Venue</span>
                <span class="meta-value">${d.event.venue}</span>
            </div>
            <div class="bandobast-meta-item">
                <span class="meta-label">Date</span>
                <span class="meta-value">${d.shift.date} (${d.shift.day})</span>
            </div>
            <div class="bandobast-meta-item">
                <span class="meta-label">Duty Hours</span>
                <span class="meta-value">${d.shift.start} — ${d.shift.end} (${d.shift.total_hours} hrs)</span>
            </div>
            <div class="bandobast-meta-item">
                <span class="meta-label">Expected Crowd</span>
                <span class="meta-value">${formatNumber(d.event.expected_crowd)}</span>
            </div>
            <div class="bandobast-meta-item">
                <span class="meta-label">Extra Constables</span>
                <span class="meta-value">${d.resources.extra_constables_needed}</span>
            </div>
            <div class="bandobast-meta-item">
                <span class="meta-label">Barricades</span>
                <span class="meta-value">${d.resources.barricades} (${d.event.barricade_type})</span>
            </div>
            <div class="bandobast-meta-item">
                <span class="meta-label">Signal Overrides</span>
                <span class="meta-value">${d.resources.signal_overrides}</span>
            </div>
        </div>

        <div class="bandobast-assignments">
            <h4>Junction Assignments (${activeAssignments.length} positions)</h4>
            ${activeAssignments.map(a => `
                <div class="assignment-card severity-${a.severity}">
                    <div>
                        <div class="assignment-name">${a.junction_name}</div>
                        <div class="assignment-zone">${a.zone} • ${a.shift_start} — ${a.shift_end}</div>
                        <ul class="assignment-instructions">
                            ${a.instructions.map(i => `<li>${i}</li>`).join('')}
                        </ul>
                    </div>
                    <div class="assignment-constables">
                        <div class="constable-count">${a.total_constables}</div>
                        <div class="constable-label">Constables<br>(+${a.extra_constables} extra)</div>
                    </div>
                </div>
            `).join('')}
        </div>

        ${d.diversions.length > 0 ? `
        <div class="bandobast-diversions">
            <h4>Diversion Routes (${d.diversions.length})</h4>
            ${d.diversions.map(div => `
                <div class="diversion-item">
                    <span class="diversion-icon">🔀</span>
                    <div class="diversion-details">
                        <div class="diversion-from">${div.from_direction}</div>
                        <div class="diversion-via">via ${div.via_route}</div>
                    </div>
                    <span class="diversion-saves">Saves ~${div.estimated_time_saved_min} min</span>
                </div>
            `).join('')}
        </div>` : ''}
    `;
}

// ─── Economic Impact ───
function renderEconomics(data) {
    const ec = data.economics;
    const grid = document.getElementById('economicsGrid');

    grid.innerHTML = `
        <div class="economics-card without">
            <h3>❌ Without Deployment</h3>
            <div class="econ-row">
                <span class="econ-label">Fuel Waste</span>
                <span class="econ-value">${formatINR(ec.without_deployment.fuel_waste)}</span>
            </div>
            <div class="econ-row">
                <span class="econ-label">Productivity Loss</span>
                <span class="econ-value">${formatINR(ec.without_deployment.productivity_loss)}</span>
            </div>
            <div class="econ-row">
                <span class="econ-label">Flipkart Delivery Cost</span>
                <span class="econ-value">${formatINR(ec.without_deployment.flipkart_delivery_cost)}</span>
            </div>
            <div class="econ-row">
                <span class="econ-label">Emergency Response</span>
                <span class="econ-value">${ec.without_deployment.emergency_response_min} min</span>
            </div>
            <div class="econ-row">
                <span class="econ-label">CO₂ Emissions</span>
                <span class="econ-value">${formatNumber(ec.without_deployment.co2_emissions_kg)} kg</span>
            </div>
            <div class="econ-row">
                <span class="econ-label"><strong>Total Economic Loss</strong></span>
                <span class="econ-value econ-total" style="color:var(--accent-red)">${formatINR(ec.without_deployment.total_cost)}</span>
            </div>
        </div>

        <div class="economics-card with">
            <h3>✅ With Deployment</h3>
            <div class="econ-row">
                <span class="econ-label">Fuel Waste</span>
                <span class="econ-value">${formatINR(ec.with_deployment.fuel_waste)}</span>
            </div>
            <div class="econ-row">
                <span class="econ-label">Productivity Loss</span>
                <span class="econ-value">${formatINR(ec.with_deployment.productivity_loss)}</span>
            </div>
            <div class="econ-row">
                <span class="econ-label">Flipkart Delivery Cost</span>
                <span class="econ-value">${formatINR(ec.with_deployment.flipkart_delivery_cost)}</span>
            </div>
            <div class="econ-row">
                <span class="econ-label">Emergency Response</span>
                <span class="econ-value">${ec.with_deployment.emergency_response_min} min</span>
            </div>
            <div class="econ-row">
                <span class="econ-label">Deployment Investment</span>
                <span class="econ-value">${formatINR(ec.with_deployment.deployment_cost)}</span>
            </div>
            <div class="econ-row">
                <span class="econ-label"><strong>Total Cost (incl. deployment)</strong></span>
                <span class="econ-value econ-total" style="color:var(--accent-green)">${formatINR(ec.with_deployment.total_cost)}</span>
            </div>
        </div>

        <div class="savings-banner">
            <div class="savings-title">Net Savings from Deployment</div>
            <div class="savings-value">${formatINR(ec.savings.net_savings)}</div>
            <div class="savings-sub">ROI: ${ec.savings.roi_percentage}% return on deployment investment</div>
            <div class="savings-details">
                <div class="savings-detail-item">
                    <div class="savings-detail-value">${formatNumber(ec.savings.person_hours_recovered)}</div>
                    <div class="savings-detail-label">Person-Hours Saved</div>
                </div>
                <div class="savings-detail-item">
                    <div class="savings-detail-value">${ec.savings.emergency_response_improvement_min} min</div>
                    <div class="savings-detail-label">Faster Emergency Response</div>
                </div>
                <div class="savings-detail-item">
                    <div class="savings-detail-value">${formatNumber(ec.savings.co2_reduced_kg)} kg</div>
                    <div class="savings-detail-label">CO₂ Reduced</div>
                </div>
            </div>
        </div>
    `;
}

// ─── Flipkart Section ───
function renderFlipkart(data) {
    const ec = data.economics;
    const grid = document.getElementById('flipkartGrid');

    grid.innerHTML = `
        <div class="flipkart-card">
            <span class="fk-icon">📦</span>
            <span class="fk-value">${formatNumber(ec.without_deployment.deliveries_delayed)}</span>
            <span class="fk-label">Deliveries Delayed (No Deploy)</span>
            <span class="fk-compare bad">Impact: ${formatINR(ec.without_deployment.flipkart_delivery_cost)}</span>
        </div>
        <div class="flipkart-card">
            <span class="fk-icon">✅</span>
            <span class="fk-value">${formatNumber(ec.with_deployment.deliveries_delayed)}</span>
            <span class="fk-label">Deliveries Delayed (With Deploy)</span>
            <span class="fk-compare good">Reduced by ${formatNumber(ec.savings.flipkart_deliveries_saved)} orders</span>
        </div>
        <div class="flipkart-card">
            <span class="fk-icon">💰</span>
            <span class="fk-value">${formatINR(ec.savings.flipkart_deliveries_saved * 45)}</span>
            <span class="fk-label">Flipkart Cost Saved</span>
            <span class="fk-compare good">Per event deployment</span>
        </div>
        <div class="flipkart-card">
            <span class="fk-icon">🚚</span>
            <span class="fk-value">${data.impact.impact_summary.affected_junctions}</span>
            <span class="fk-label">Delivery Zones Impacted</span>
            <span class="fk-compare bad">Active during event window</span>
        </div>
    `;
}

// ─── WhatsApp Alert ───
function renderWhatsApp(data) {
    const body = document.getElementById('whatsappBody');
    const alert = data.deployment.whatsapp_alert;
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

    // Convert markdown-style bold to HTML
    const formatted = alert
        .replace(/\*([^*]+)\*/g, '<strong>$1</strong>')
        .replace(/_([^_]+)_/g, '<em style="color:#8696a0;">$1</em>');

    body.innerHTML = `
        <div class="wa-message">
            ${formatted}
            <div class="wa-time">${timeStr} ✓✓</div>
        </div>
    `;
}

// ─── Set default date to near future ───
document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('eventDate');
    const today = new Date();
    today.setDate(today.getDate() + 6);
    dateInput.value = today.toISOString().split('T')[0];
});
