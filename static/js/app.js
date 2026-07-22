/**
 * ASTraM Command Center — Bengaluru Traffic Police
 * Event Traffic Demand & Dispatch System
 */

// Global State
let map = null;
let currentResult = null;
let previousResult = null;
let activeView = 'map';
let currentSortColumn = null;
let currentSortDirection = 'asc';
let junctionData = [];
let clockInterval = null;
let countdownInterval = null;
let eventDateTime = null;
let mapInitialized = false;
let activeSeverityFilter = 'all';
let allMapMarkers = [];

// Theme State
let currentTheme = localStorage.getItem('btp_theme') || 'dark';

// 3D Tactical View State
let scene3D = null;
let camera3D = null;
let renderer3D = null;
let controls3D = null;
let scene3DInitialized = false;

let trafficParticlesGroup = null;
let crowdParticlesGroup = null;
let carsGroup = null;
let bikesGroup = null;
let busesGroup = null;
let constablesGroup = null;
let barricadesGroup = null;
let junctionBeaconsGroup = null;

let showParticles3D = true;
let showBeacons3D = true;
let animationFrameId3D = null;

// History Config
const HISTORY_KEY = 'btp_astram_event_history';
const MAX_HISTORY = 5;

// Helper Functions
function formatINR(amount) {
    if (amount >= 10000000) return '₹' + (amount / 10000000).toFixed(2) + ' Cr';
    if (amount >= 100000) return '₹' + (amount / 100000).toFixed(2) + ' L';
    if (amount >= 1000) return '₹' + (amount / 1000).toFixed(1) + 'K';
    return '₹' + amount.toLocaleString('en-IN');
}

function formatNumber(n) {
    return n.toLocaleString('en-IN');
}

// Theme Switcher
function initTheme() {
    applyTheme(currentTheme);
    document.getElementById('themeToggleBtn').addEventListener('click', () => {
        currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('btp_theme', currentTheme);
        applyTheme(currentTheme);
    });
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const icon = document.getElementById('themeIcon');
    const label = document.getElementById('themeLabel');
    if (theme === 'light') {
        icon.textContent = '☀️';
        label.textContent = 'Light Mode';
    } else {
        icon.textContent = '🌙';
        label.textContent = 'Dark Mode';
    }

    if (map) {
        setTimeout(() => map.invalidateSize(), 200);
    }
}

// Counter animation
function animateCounter(el, target, duration = 800, prefix = '', suffix = '') {
    if (!el) return;
    const start = 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(start + (target - start) * eased);
        el.textContent = prefix + formatNumber(current) + suffix;

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    requestAnimationFrame(update);
}

// Live Clock & Event Countdown
function startClock() {
    const clockEl = document.getElementById('clockTime');
    function tick() {
        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString('en-IN', {
            hour: '2-digit', minute: '2-digit', second: '2-digit',
            hour12: false, timeZone: 'Asia/Kolkata'
        });
    }
    tick();
    clockInterval = setInterval(tick, 1000);
}

function startCountdown(dateStr, timeStr) {
    const countdownEl = document.getElementById('navCountdown');
    const countdownText = document.getElementById('countdownText');
    eventDateTime = new Date(`${dateStr}T${timeStr}:00+05:30`);

    function updateCountdown() {
        const now = new Date();
        const diff = eventDateTime - now;
        if (diff <= 0) {
            countdownText.textContent = 'Event NOW';
            countdownEl.style.display = 'flex';
            clearInterval(countdownInterval);
            return;
        }
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        let text = '';
        if (days > 0) text += `${days}d `;
        text += `${hours}h ${mins}m`;
        countdownText.textContent = `Event in ${text}`;
        countdownEl.style.display = 'flex';
    }

    if (countdownInterval) clearInterval(countdownInterval);
    updateCountdown();
    countdownInterval = setInterval(updateCountdown, 60000);
}

// View switching
function initViews() {
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            switchView(btn.dataset.view);
        });
    });

    // 3D tab is only available for stadium venues that have a tactical model
    const venueSelect = document.getElementById('venueSelect');
    if (venueSelect) {
        venueSelect.addEventListener('change', onVenueChange);
        update3DTabVisibility();
    }
}

// Venues supporting 3D spatial tactical model (M. Chinnaswamy Stadium)
const STADIUM_VENUES = ['chinnaswamy'];

function update3DTabVisibility() {
    const venueSelect = document.getElementById('venueSelect');
    const btn3D = document.getElementById('viewBtn3D');
    if (!venueSelect || !btn3D) return;

    const isStadium = STADIUM_VENUES.includes(venueSelect.value);
    btn3D.style.display = isStadium ? '' : 'none';

    // If currently on 3D view and venue changed away from Chinnaswamy, fall back to map
    if (!isStadium && activeView === '3d') {
        switchView('map');
    }
}

function onVenueChange() {
    update3DTabVisibility();
}

function switchView(viewName) {
    activeView = viewName;

    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === viewName);
    });

    document.querySelectorAll('.view-panel').forEach(panel => {
        const isActive = panel.dataset.view === viewName;
        panel.classList.toggle('active', isActive);
    });

    if (viewName === 'map' && map) {
        setTimeout(() => map.invalidateSize(), 150);
    } else if (viewName === '3d') {
        if (!scene3DInitialized) {
            init3DTacticalScene();
        } else if (renderer3D) {
            on3DWindowResize();
        }
    }
}

// Keyboard shortcuts
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;

        switch (e.key.toLowerCase()) {
            case 'm': switchView('map'); break;
            case 'a': switchView('analytics'); break;
            case 'o': switchView('operations'); break;
            case '3':
                if (STADIUM_VENUES.includes(document.getElementById('venueSelect')?.value)) {
                    switchView('3d');
                }
                break;
            case 'h': toggleHistorySidebar(); break;
            case 'escape':
                closeSpotlight();
                closeHistorySidebar();
                break;
        }
    });
}

// Alert level status indicator
function updateAlertLevel(data) {
    const alertEl = document.getElementById('alertLevel');
    const alertDot = alertEl.querySelector('.alert-dot');
    const alertText = document.getElementById('alertText');

    const summary = data.impact.impact_summary;
    let level = 'green';
    let text = 'NORMAL';

    if (summary.critical_junctions > 3) {
        level = 'red';
        text = 'CRITICAL ALERT';
    } else if (summary.critical_junctions > 0 || summary.high_junctions > 3) {
        level = 'amber';
        text = 'HIGH ALERT';
    } else if (summary.high_junctions > 0) {
        level = 'amber';
        text = 'ELEVATED';
    }

    alertEl.className = 'alert-level ' + level;
    alertDot.className = 'alert-dot ' + level;
    alertText.textContent = text;
}

// Map filter chips
function initFilterChips() {
    document.querySelectorAll('.filter-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');

            activeSeverityFilter = chip.dataset.severity;
            filterMapMarkers();
        });
    });
}

function filterMapMarkers() {
    allMapMarkers.forEach(({ marker, severity }) => {
        if (activeSeverityFilter === 'all') {
            if (!map.hasLayer(marker)) map.addLayer(marker);
        } else {
            const match = severity.toLowerCase() === activeSeverityFilter;
            if (match && !map.hasLayer(marker)) map.addLayer(marker);
            else if (!match && map.hasLayer(marker)) map.removeLayer(marker);
        }
    });
}

// Junction spotlight overlay
function showSpotlight(junction) {
    const panel = document.getElementById('spotlightPanel');
    const content = document.getElementById('spotlightContent');

    content.innerHTML = `
        <div class="spotlight-name">${junction.name}</div>
        <div class="spotlight-zone">${junction.zone} Zone • ${junction.distance_km} km from venue</div>
        <span class="spotlight-severity" style="background:${junction.color};color:${junction.severity === 'CRITICAL' || junction.severity === 'HIGH' ? '#fff' : '#12141A'}">
            ${junction.severity}
        </span>
        <div class="spotlight-metrics">
            <div class="spotlight-metric">
                <span class="spotlight-metric-label">Capacity Ratio</span>
                <span class="spotlight-metric-value">${junction.capacity_ratio}x</span>
            </div>
            <div class="spotlight-metric">
                <span class="spotlight-metric-label">Delay (No Deploy)</span>
                <span class="spotlight-metric-value" style="color:var(--signal-red)">${junction.delay_without_deployment_min} min</span>
            </div>
            <div class="spotlight-metric">
                <span class="spotlight-metric-label">Delay (With Deploy)</span>
                <span class="spotlight-metric-value" style="color:var(--signal-green)">${junction.delay_with_deployment_min} min</span>
            </div>
            <div class="spotlight-metric">
                <span class="spotlight-metric-label">Constables Needed</span>
                <span class="spotlight-metric-value">${junction.total_constables} (+${junction.extra_constables_needed})</span>
            </div>
        </div>
    `;

    panel.style.display = 'block';

    if (map) {
        map.flyTo([junction.lat, junction.lon], 15, { duration: 0.8 });
    }
}

function closeSpotlight() {
    document.getElementById('spotlightPanel').style.display = 'none';
}

// Bottom live ticker
function renderTicker(data) {
    const ticker = document.getElementById('tickerContent');
    const junctions = data.impact.junction_impacts;

    if (!junctions || junctions.length === 0) {
        ticker.innerHTML = '<span class="ticker-item standby">No active junction alerts</span>';
        return;
    }

    const items = junctions.map(j =>
        `<span class="ticker-item">
            <span class="ticker-sev ${j.severity.toLowerCase()}"></span>
            <span class="ticker-name">${j.name}</span>
            <span class="ticker-detail">${j.severity} • ${j.delay_without_deployment_min}m delay • ${j.total_constables} constables</span>
        </span>`
    ).join('<span class="ticker-sep">│</span>');

    ticker.innerHTML = items + '<span class="ticker-sep">│</span>' + items;
}

// Zone Breakdown
function renderZoneBreakdown(data) {
    const zoneList = document.getElementById('zoneList');
    const junctions = data.impact.junction_impacts;

    if (!junctions || junctions.length === 0) {
        zoneList.innerHTML = '<div style="font-size:11px;color:var(--chalk-muted);padding:8px;">No data</div>';
        return;
    }

    const zones = {};
    junctions.forEach(j => {
        if (!zones[j.zone]) {
            zones[j.zone] = { critical: 0, high: 0, moderate: 0, low: 0 };
        }
        zones[j.zone][j.severity.toLowerCase()]++;
    });

    const sortedZones = Object.entries(zones).sort((a, b) => {
        const scoreA = a[1].critical * 4 + a[1].high * 3 + a[1].moderate * 2 + a[1].low;
        const scoreB = b[1].critical * 4 + b[1].high * 3 + b[1].moderate * 2 + b[1].low;
        return scoreB - scoreA;
    });

    zoneList.innerHTML = sortedZones.map(([name, counts], i) => {
        const badges = [];
        if (counts.critical > 0) badges.push(`<span class="zone-badge critical">${counts.critical}C</span>`);
        if (counts.high > 0) badges.push(`<span class="zone-badge high">${counts.high}H</span>`);
        if (counts.moderate > 0) badges.push(`<span class="zone-badge moderate">${counts.moderate}M</span>`);
        if (counts.low > 0) badges.push(`<span class="zone-badge low">${counts.low}L</span>`);

        return `
            <div class="zone-item" style="animation-delay:${i * 0.05}s">
                <span class="zone-name">${name}</span>
                <div class="zone-badges">${badges.join('')}</div>
            </div>
        `;
    }).join('');
}

// History sidebar
function initHistory() {
    document.getElementById('historyToggleBtn').addEventListener('click', toggleHistorySidebar);
    document.getElementById('historyCloseBtn').addEventListener('click', closeHistorySidebar);
    document.getElementById('historyOverlay').addEventListener('click', closeHistorySidebar);
    document.getElementById('historyClearBtn').addEventListener('click', clearHistory);
    renderHistory();
}

function toggleHistorySidebar() {
    const sidebar = document.getElementById('historySidebar');
    const overlay = document.getElementById('historyOverlay');
    const isOpen = sidebar.classList.contains('open');
    sidebar.classList.toggle('open', !isOpen);
    overlay.classList.toggle('active', !isOpen);
}

function closeHistorySidebar() {
    document.getElementById('historySidebar').classList.remove('open');
    document.getElementById('historyOverlay').classList.remove('active');
}

function getHistory() {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }
    catch { return []; }
}

function saveToHistory(data) {
    const history = getHistory();
    const entry = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        event: data.impact.event,
        summary: data.impact.impact_summary,
        savings: data.economics.savings,
        fullData: data,
    };
    history.unshift(entry);
    if (history.length > MAX_HISTORY) history.pop();
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    renderHistory();
    updateHistoryCount();
}

function updateHistoryCount() {
    const count = getHistory().length;
    const badge = document.getElementById('historyCount');
    if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'flex';
    } else {
        badge.style.display = 'none';
    }
}

function renderHistory() {
    const list = document.getElementById('historyList');
    const history = getHistory();

    if (history.length === 0) {
        list.innerHTML = `
            <div class="history-empty">
                <span class="history-empty-icon">🕐</span>
                <p>No predictions yet</p>
                <p class="history-empty-sub">Run your first prediction to see history here</p>
            </div>
        `;
        return;
    }

    list.innerHTML = history.map((entry, idx) => {
        const time = new Date(entry.timestamp);
        const timeStr = time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
        const dateStr = time.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });

        return `
            <div class="history-item ${idx === 0 && currentResult ? 'active' : ''}" onclick="loadHistoryEntry(${entry.id})">
                <div class="history-item-header">
                    <span class="history-item-icon">${entry.event.icon}</span>
                    <span class="history-item-title">${entry.event.type_name}</span>
                    <span class="history-item-time">${dateStr} ${timeStr}</span>
                </div>
                <div class="history-item-meta">
                    <span class="history-meta-tag">📍 ${entry.event.venue}</span>
                    <span class="history-meta-tag">👥 ${formatNumber(entry.event.expected_crowd)}</span>
                    <span class="history-meta-tag">🚧 ${entry.summary.affected_junctions} junctions</span>
                </div>
            </div>
        `;
    }).join('');
}

function loadHistoryEntry(id) {
    const history = getHistory();
    const entry = history.find(h => h.id === id);
    if (!entry) return;

    currentResult = entry.fullData;
    renderResults(entry.fullData);
    closeHistorySidebar();
    switchView('map');
}

function clearHistory() {
    localStorage.removeItem(HISTORY_KEY);
    renderHistory();
    updateHistoryCount();
    previousResult = null;
}

// Table sort & filtering
function initTableControls() {
    document.querySelectorAll('.impact-table th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const sortKey = th.dataset.sort;
            if (currentSortColumn === sortKey) {
                currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                currentSortColumn = sortKey;
                currentSortDirection = 'asc';
            }

            document.querySelectorAll('.impact-table th.sortable').forEach(h => h.classList.remove('sort-active'));
            th.classList.add('sort-active');
            th.querySelector('.sort-arrow').textContent = currentSortDirection === 'asc' ? '↑' : '↓';
            renderFilteredTable();
        });
    });

    document.getElementById('severityFilter').addEventListener('change', renderFilteredTable);
}

function renderFilteredTable() {
    if (!junctionData.length) return;
    let filtered = [...junctionData];

    const filterVal = document.getElementById('severityFilter').value;
    if (filterVal === 'critical') {
        filtered = filtered.filter(j => j.severity === 'CRITICAL');
    } else if (filterVal === 'critical-high') {
        filtered = filtered.filter(j => ['CRITICAL', 'HIGH'].includes(j.severity));
    } else if (filterVal === 'critical-high-moderate') {
        filtered = filtered.filter(j => ['CRITICAL', 'HIGH', 'MODERATE'].includes(j.severity));
    }

    if (currentSortColumn) {
        const severityOrder = { CRITICAL: 0, HIGH: 1, MODERATE: 2, LOW: 3 };
        filtered.sort((a, b) => {
            let valA, valB;
            switch (currentSortColumn) {
                case 'name': valA = a.name; valB = b.name; break;
                case 'zone': valA = a.zone; valB = b.zone; break;
                case 'distance': valA = a.distance_km; valB = b.distance_km; break;
                case 'severity': valA = severityOrder[a.severity]; valB = severityOrder[b.severity]; break;
                case 'capacity': valA = a.capacity_ratio; valB = b.capacity_ratio; break;
                case 'delay_without': valA = a.delay_without_deployment_min; valB = b.delay_without_deployment_min; break;
                case 'delay_with': valA = a.delay_with_deployment_min; valB = b.delay_with_deployment_min; break;
                case 'constables': valA = a.total_constables; valB = b.total_constables; break;
                default: return 0;
            }
            if (typeof valA === 'string') {
                const cmp = valA.localeCompare(valB);
                return currentSortDirection === 'asc' ? cmp : -cmp;
            }
            return currentSortDirection === 'asc' ? valA - valB : valB - valA;
        });
    }

    const tbody = document.getElementById('impactTableBody');
    tbody.innerHTML = filtered.map(j => `
        <tr onclick="handleTableRowClick('${j.name.replace(/'/g, "\\'")}')">
            <td><strong>${j.name}</strong></td>
            <td>${j.zone}</td>
            <td>${j.distance_km}</td>
            <td><span class="severity-badge ${j.severity}">${j.severity}</span></td>
            <td>${j.capacity_ratio}x</td>
            <td style="color:var(--signal-red);font-weight:600">${j.delay_without_deployment_min} min</td>
            <td style="color:var(--signal-green);font-weight:600">${j.delay_with_deployment_min} min</td>
            <td><strong>${j.total_constables}</strong> <span style="color:var(--chalk-muted)">(+${j.extra_constables_needed})</span></td>
        </tr>
    `).join('');

    document.getElementById('tableFooter').textContent = `Showing ${filtered.length} of ${junctionData.length} junctions`;
}

function handleTableRowClick(name) {
    if (!currentResult) return;
    const junction = currentResult.impact.junction_impacts.find(j => j.name === name);
    if (junction) {
        switchView('map');
        setTimeout(() => showSpotlight(junction), 300);
    }
}

// WhatsApp Dispatch Handler
function triggerWhatsAppDispatch() {
    const btn = document.getElementById('dispatchTriggerBtn');
    const statusText = document.getElementById('dispatchStatusText');

    if (!currentResult) {
        alert('Please run a prediction first before broadcasting alerts.');
        return;
    }

    const extraConstables = currentResult.impact.impact_summary.total_extra_constables;
    btn.disabled = true;
    btn.innerHTML = `<span class="dispatch-btn-icon">🔄</span> Dispatching to ${extraConstables} Constables...`;
    statusText.textContent = `Dispatching broadcast alert...`;
    statusText.style.color = '#e8a838';

    setTimeout(() => {
        btn.innerHTML = `<span class="dispatch-btn-icon">✓</span> Sent to ${extraConstables} On-Duty Officers`;
        btn.style.background = '#2e7d32';
        statusText.textContent = `Alert Delivered (${new Date().toLocaleTimeString('en-IN', {hour:'2-digit', minute:'2-digit'})})`;
        statusText.style.color = '#38c868';
    }, 1500);
}

// Export Report Handler
function exportReport() {
    switchView('operations');
    setTimeout(() => window.print(), 300);
}

// API Call: Prediction Engine
async function runPrediction() {
    const btn = document.getElementById('predictBtn');
    const loader = document.getElementById('loadingOverlay');

    const payload = {
        event_type: document.getElementById('eventType').value,
        venue_id: document.getElementById('venueSelect').value,
        event_date: document.getElementById('eventDate').value,
        event_time: document.getElementById('eventTime').value,
        expected_crowd: document.getElementById('expectedCrowd').value || null,
    };

    btn.disabled = true;
    loader.classList.add('active');

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

        if (currentResult) {
            previousResult = currentResult;
        }

        currentResult = data;
        renderResults(data);
        saveToHistory(data);
        startCountdown(payload.event_date, payload.event_time);
        switchView('map');

    } catch (err) {
        alert('Error connecting to server: ' + err.message);
    } finally {
        btn.disabled = false;
        loader.classList.remove('active');
    }
}

// Render Results Pipeline
function renderResults(data) {
    document.getElementById('statsSection').style.display = 'block';
    document.getElementById('zoneSection').style.display = 'block';
    document.getElementById('mapWelcome').style.display = 'none';
    document.getElementById('mapWrapper').style.display = 'flex';

    updateAlertLevel(data);

    renderQuickStats(data);
    renderZoneBreakdown(data);
    renderMap(data);
    renderTicker(data);
    renderJunctionGrid(data);
    renderSummary(data);
    renderTimeline(data);
    renderImpactTable(data);
    renderBandobast(data);
    renderEconomics(data);
    renderFlipkart(data);
    renderWhatsApp(data);

    if (scene3DInitialized) {
        update3DBeacons(data);
    }
}

// Quick Stats
function renderQuickStats(data) {
    const event = data.impact.event;
    const summary = data.impact.impact_summary;
    const savings = data.economics.savings;

    document.getElementById('eventBadge').textContent = `${event.icon} ${event.type_name}`;

    animateCounter(document.getElementById('statCrowd'), event.expected_crowd, 1000);
    animateCounter(document.getElementById('statJunctions'), summary.affected_junctions, 600);
    animateCounter(document.getElementById('statDelay'), summary.delay_reduction_pct, 800, '', '%');
    animateCounter(document.getElementById('statConstables'), summary.total_extra_constables, 700);
    document.getElementById('statSavings').textContent = formatINR(savings.net_savings);
}

// Junction Status Matrix
function renderJunctionGrid(data) {
    const grid = document.getElementById('junctionGrid');
    const junctions = data.impact.junction_impacts;
    const countEl = document.getElementById('junctionBoardCount');

    countEl.textContent = `${junctions.length} junctions`;

    if (!junctions || junctions.length === 0) {
        grid.innerHTML = '<div style="color:var(--chalk-muted);font-size:11px;padding:16px;text-align:center;">No affected junctions.</div>';
        return;
    }

    grid.innerHTML = junctions.map(j => {
        const sevClass = j.severity.toLowerCase();
        const titleText = `${j.name} | ${j.severity} | ${j.delay_without_deployment_min}m delay | ${j.total_constables} constables`;
        return `<div class="junction-cell sev-${sevClass}" title="${titleText}" onclick="handleJunctionCellClick('${j.name.replace(/'/g, "\\'")}')"></div>`;
    }).join('');
}

function handleJunctionCellClick(name) {
    if (!currentResult) return;
    const junction = currentResult.impact.junction_impacts.find(j => j.name === name);
    if (junction) {
        switchView('map');
        setTimeout(() => showSpotlight(junction), 300);
    }
}

// Summary Cards
function renderSummary(data) {
    const event = data.impact.event;
    const summary = data.impact.impact_summary;
    const grid = document.getElementById('summaryGrid');

    grid.innerHTML = `
        <div class="summary-card blue"><span class="card-accent"></span>
            <span class="card-value">${formatNumber(event.expected_crowd)}</span>
            <span class="card-label">Expected Crowd</span>
            <span class="card-sub">${formatNumber(event.vehicles_generated)} vehicles</span>
        </div>
        <div class="summary-card red"><span class="card-accent"></span>
            <span class="card-value">${summary.affected_junctions}</span>
            <span class="card-label">Junctions Affected</span>
            <span class="card-sub">${summary.critical_junctions} critical, ${summary.high_junctions} high</span>
        </div>
        <div class="summary-card yellow"><span class="card-accent"></span>
            <span class="card-value">${summary.avg_delay_without_deployment_min} min</span>
            <span class="card-label">Avg Delay (No Deploy)</span>
            <span class="card-sub">${summary.impact_window_start} — ${summary.impact_window_end}</span>
        </div>
        <div class="summary-card green"><span class="card-accent"></span>
            <span class="card-value">${summary.avg_delay_with_deployment_min} min</span>
            <span class="card-label">Avg Delay (Deploy)</span>
            <span class="card-sub">${summary.delay_reduction_pct}% reduction</span>
        </div>
        <div class="summary-card purple"><span class="card-accent"></span>
            <span class="card-value">${summary.total_extra_constables}</span>
            <span class="card-label">Extra Constables</span>
            <span class="card-sub">Above normal deployment</span>
        </div>
        <div class="summary-card cyan"><span class="card-accent"></span>
            <span class="card-value">${event.impact_radius_km} km</span>
            <span class="card-label">Impact Radius</span>
            <span class="card-sub">${event.predictability} predictability</span>
        </div>
    `;
}

// 2D Leaflet Map Initialization & Rendering
function renderMap(data) {
    const event = data.impact.event;
    const junctions = data.impact.junction_impacts;
    const container = document.getElementById('mapContainer');

    if (map) {
        map.remove();
        map = null;
    }
    allMapMarkers = [];

    map = L.map(container, {
        center: [event.venue_lat, event.venue_lon],
        zoom: 13,
        zoomControl: true,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '© OpenStreetMap contributors © CARTO',
        maxZoom: 18,
    }).addTo(map);

    L.circle([event.venue_lat, event.venue_lon], {
        radius: event.impact_radius_km * 1000,
        color: 'rgba(196, 162, 101, 0.4)',
        fillColor: 'rgba(196, 162, 101, 0.05)',
        fillOpacity: 0.3,
        weight: 2,
        dashArray: '8 6',
    }).addTo(map);

    const venueIcon = L.divIcon({
        className: 'custom-div-icon',
        html: `<div style="position:relative;">
            <div style="
                position:absolute; top:-20px; left:-20px;
                width:40px; height:40px;
                background:rgba(196,162,101,0.2);
                border-radius:50%;
                animation: sonarPing 2.5s ease-out infinite;
            "></div>
            <div style="
                position:relative; z-index:2;
                width:36px;height:36px;
                background:var(--khaki,#C4A265);
                border-radius:50%;
                border:3px solid white;
                display:flex;align-items:center;justify-content:center;
                font-size:18px;
                box-shadow:0 0 24px rgba(196,162,101,0.6);
            ">${event.icon}</div>
        </div>`,
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

    junctions.forEach(j => {
        const size = j.severity === 'CRITICAL' ? 22 : j.severity === 'HIGH' ? 18 : j.severity === 'MODERATE' ? 14 : 12;
        const color = j.color;

        let markerHtml = '';
        if (j.severity === 'CRITICAL') {
            markerHtml = `<div style="position:relative;">
                <div class="sonar-ring"></div>
                <div style="
                    position:relative; z-index:2;
                    width:${size}px;height:${size}px;
                    background:${color};
                    border-radius:50%;
                    border:2px solid rgba(255,255,255,0.8);
                    box-shadow:0 0 12px ${color}80;
                    animation: criticalBlink 1.5s infinite;
                    cursor:pointer;
                "></div>
            </div>`;
        } else if (j.severity === 'HIGH') {
            markerHtml = `<div style="position:relative;">
                <div class="sonar-ring amber"></div>
                <div style="
                    position:relative; z-index:2;
                    width:${size}px;height:${size}px;
                    background:${color};
                    border-radius:50%;
                    border:2px solid rgba(255,255,255,0.6);
                    box-shadow:0 0 8px ${color}60;
                    animation: highPulse 2s infinite;
                    cursor:pointer;
                "></div>
            </div>`;
        } else {
            markerHtml = `<div style="
                width:${size}px;height:${size}px;
                background:${color};
                border-radius:50%;
                border:2px solid rgba(255,255,255,0.5);
                box-shadow:0 0 6px ${color}40;
                cursor:pointer;
            "></div>`;
        }

        const jIcon = L.divIcon({
            className: 'custom-div-icon',
            html: markerHtml,
            iconSize: [size + 10, size + 10],
            iconAnchor: [(size + 10) / 2, (size + 10) / 2],
        });

        const marker = L.marker([j.lat, j.lon], { icon: jIcon })
            .addTo(map)
            .on('click', () => showSpotlight(j));

        marker.bindPopup(`
            <div class="popup-title">${j.name}</div>
            <span class="popup-severity" style="background:${color}">${j.severity}</span>
            <div class="popup-detail">Distance: ${j.distance_km} km</div>
            <div class="popup-detail">Delay: ${j.delay_without_deployment_min}m → ${j.delay_with_deployment_min}m</div>
            <div class="popup-detail">Constables: ${j.total_constables} (+${j.extra_constables_needed})</div>
        `);

        allMapMarkers.push({ marker, severity: j.severity });

        L.polyline(
            [[event.venue_lat, event.venue_lon], [j.lat, j.lon]],
            {
                color: j.severity === 'CRITICAL' ? 'rgba(232,64,64,0.35)' : 'rgba(196,162,101,0.15)',
                weight: j.severity === 'CRITICAL' ? 2 : 1,
                dashArray: '4 6',
            }
        ).addTo(map);
    });

    const allPoints = [[event.venue_lat, event.venue_lon], ...junctions.map(j => [j.lat, j.lon])];
    if (allPoints.length > 1) {
        map.fitBounds(allPoints, { padding: [30, 30] });
    }

    setTimeout(() => map.invalidateSize(), 200);
    mapInitialized = true;
}

// Congestion Timeline
function renderTimeline(data) {
    const timeline = data.impact.timeline;
    const chart = document.getElementById('timelineChart');
    const maxCongestion = Math.max(...timeline.map(t => t.congestion_level), 1);

    chart.innerHTML = timeline.map(t => {
        const height = Math.max(6, (t.congestion_level / maxCongestion) * 160);
        let color;
        if (t.congestion_level > maxCongestion * 0.8) color = 'var(--sev-critical)';
        else if (t.congestion_level > maxCongestion * 0.5) color = 'var(--sev-high)';
        else if (t.congestion_level > maxCongestion * 0.3) color = 'var(--sev-moderate)';
        else color = 'var(--sev-low)';

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

// Impact Table
function renderImpactTable(data) {
    junctionData = data.impact.junction_impacts;
    currentSortColumn = 'severity';
    currentSortDirection = 'asc';
    renderFilteredTable();
}

// Bandobast Deployment Order
function renderBandobast(data) {
    const d = data.deployment;
    const card = document.getElementById('bandobastCard');
    const activeAssignments = d.assignments.filter(a => a.severity !== 'LOW' || a.extra_constables > 0);

    card.innerHTML = `
        <div class="bandobast-header">
            <h3>⚡ ASTraM Bandobast Order</h3>
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

// Economic ROI Summary
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
                <span class="econ-label">Logistics Delay Cost</span>
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
                <span class="econ-value econ-total" style="color:var(--signal-red)">${formatINR(ec.without_deployment.total_cost)}</span>
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
                <span class="econ-label">Logistics Delay Cost</span>
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
                <span class="econ-label"><strong>Total Cost</strong></span>
                <span class="econ-value econ-total" style="color:var(--signal-green)">${formatINR(ec.with_deployment.total_cost)}</span>
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
                    <div class="savings-detail-label">Faster Emergency</div>
                </div>
                <div class="savings-detail-item">
                    <div class="savings-detail-value">${formatNumber(ec.savings.co2_reduced_kg)} kg</div>
                    <div class="savings-detail-label">CO₂ Reduced</div>
                </div>
            </div>
        </div>
    `;
}

// Flipkart Delivery Impact
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
            <span class="fk-label">Logistics Cost Saved</span>
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

// WhatsApp Alert Formatter
function renderWhatsApp(data) {
    const body = document.getElementById('whatsappBody');
    const alert = data.deployment.whatsapp_alert;
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

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

// ══════════════════════════════════════
// Three.js 3D Tactical Scene Engine
// ══════════════════════════════════════
function init3DTacticalScene() {
    const container = document.getElementById('tactical3DCanvas');
    if (!container || typeof THREE === 'undefined') return;

    scene3D = new THREE.Scene();
    scene3D.background = new THREE.Color(0x090b10);
    scene3D.fog = new THREE.FogExp2(0x090b10, 0.0022);

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 500;

    camera3D = new THREE.PerspectiveCamera(45, width / height, 1, 1200);
    camera3D.position.set(0, 170, 230);

    renderer3D = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer3D.setSize(width, height);
    renderer3D.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer3D.shadowMap.enabled = true;
    container.appendChild(renderer3D.domElement);

    if (typeof THREE.OrbitControls !== 'undefined') {
        controls3D = new THREE.OrbitControls(camera3D, renderer3D.domElement);
        controls3D.enableDamping = true;
        controls3D.dampingFactor = 0.05;
        controls3D.maxPolarAngle = Math.PI / 2 - 0.05;
        controls3D.minDistance = 40;
        controls3D.maxDistance = 450;
    }

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.45);
    scene3D.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xc4a265, 0.85);
    dirLight.position.set(120, 220, 120);
    dirLight.castShadow = true;
    scene3D.add(dirLight);

    const pointLight = new THREE.PointLight(0x38c868, 1.2, 350);
    pointLight.position.set(0, 60, 0);
    scene3D.add(pointLight);

    trafficParticlesGroup = new THREE.Group();
    crowdParticlesGroup = new THREE.Group();
    carsGroup = new THREE.Group();
    bikesGroup = new THREE.Group();
    busesGroup = new THREE.Group();
    constablesGroup = new THREE.Group();
    barricadesGroup = new THREE.Group();
    junctionBeaconsGroup = new THREE.Group();

    scene3D.add(trafficParticlesGroup);
    scene3D.add(crowdParticlesGroup);
    scene3D.add(carsGroup);
    scene3D.add(bikesGroup);
    scene3D.add(busesGroup);
    scene3D.add(constablesGroup);
    scene3D.add(barricadesGroup);
    scene3D.add(junctionBeaconsGroup);

    build3DGround();
    build3DChinnaswamyStadiumWithSign();
    build3DRoadsAndArchitecturalGrid();
    build3DTreesAndLandscaping();
    build3DPotholes();
    build3DTeamBuses();
    build3DPoliceBarricades();
    build3DFansAndCrowd();
    build3DTwoWayVehiclesAndBikes();
    build3DPoliceConstables();

    if (currentResult) {
        update3DBeacons(currentResult);
    }

    window.addEventListener('resize', on3DWindowResize);

    scene3DInitialized = true;
    animate3DScene();
}

function build3DGround() {
    const gridHelper = new THREE.GridHelper(500, 50, 0xc4a265, 0x1e212b);
    gridHelper.position.y = -0.5;
    scene3D.add(gridHelper);

    const groundGeo = new THREE.PlaneGeometry(500, 500);
    const groundMat = new THREE.MeshLambertMaterial({ color: 0x0c0e14 });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -1;
    scene3D.add(ground);
}

function build3DChinnaswamyStadiumWithSign() {
    const stadiumGroup = new THREE.Group();

    // Stadium outer wall
    const wallGeo = new THREE.CylinderGeometry(36, 33, 18, 32, 1, true);
    const wallMat = new THREE.MeshPhongMaterial({ color: 0x1e212b, side: THREE.DoubleSide });
    const wall = new THREE.Mesh(wallGeo, wallMat);
    wall.position.y = 9;
    stadiumGroup.add(wall);

    // Gold stand roof ring
    const roofGeo = new THREE.RingGeometry(26, 40, 32);
    const roofMat = new THREE.MeshPhongMaterial({ color: 0xc4a265, side: THREE.DoubleSide, opacity: 0.88, transparent: true });
    const roof = new THREE.Mesh(roofGeo, roofMat);
    roof.rotation.x = Math.PI / 2;
    roof.position.y = 18.5;
    stadiumGroup.add(roof);

    // Pitch & wickets
    const pitchGeo = new THREE.CylinderGeometry(25, 25, 1, 32);
    const pitchMat = new THREE.MeshLambertMaterial({ color: 0x2e7d32 });
    const pitch = new THREE.Mesh(pitchGeo, pitchMat);
    pitch.position.y = 0.5;
    stadiumGroup.add(pitch);

    const wicketGeo = new THREE.BoxGeometry(3, 0.2, 13);
    const wicketMat = new THREE.MeshLambertMaterial({ color: 0xd4b275 });
    const wicket = new THREE.Mesh(wicketGeo, wicketMat);
    wicket.position.y = 1.1;
    stadiumGroup.add(wicket);

    // Floodlight towers
    const towerAngles = [Math.PI / 4, (3 * Math.PI) / 4, (5 * Math.PI) / 4, (7 * Math.PI) / 4];
    towerAngles.forEach(angle => {
        const radius = 44;
        const x = Math.cos(angle) * radius;
        const z = Math.sin(angle) * radius;

        const towerGeo = new THREE.CylinderGeometry(0.8, 1.3, 38, 8);
        const towerMat = new THREE.MeshPhongMaterial({ color: 0xa9a49b });
        const tower = new THREE.Mesh(towerGeo, towerMat);
        tower.position.set(x, 19, z);
        stadiumGroup.add(tower);

        const lightGeo = new THREE.BoxGeometry(7, 4.5, 2.5);
        const lightMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
        const lightBox = new THREE.Mesh(lightGeo, lightMat);
        lightBox.position.set(x, 38, z);
        stadiumGroup.add(lightBox);
    });

    // 3D Stadium signboard
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#12141a';
    ctx.fillRect(0, 0, 512, 128);
    ctx.strokeStyle = '#c4a265';
    ctx.lineWidth = 8;
    ctx.strokeRect(4, 4, 504, 120);
    ctx.fillStyle = '#c4a265';
    ctx.font = 'bold 36px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('M. CHINNASWAMY STADIUM', 256, 56);
    ctx.fillStyle = '#ffffff';
    ctx.font = '22px sans-serif';
    ctx.fillText('BENGALURU • GATE 1 / 2 / 12', 256, 96);

    const texture = new THREE.CanvasTexture(canvas);
    const bannerGeo = new THREE.PlaneGeometry(50, 12.5);
    const bannerMat = new THREE.MeshBasicMaterial({ map: texture, side: THREE.DoubleSide, transparent: true });
    const banner = new THREE.Mesh(bannerGeo, bannerMat);
    banner.position.set(0, 32, 0);
    stadiumGroup.add(banner);

    // Stadium gates
    const gatePositions = [
        { name: 'GATE 1 (MAIN)', angle: 0 },
        { name: 'GATE 2 (PUBLIC)', angle: Math.PI / 2 },
        { name: 'GATE 12 (VIP)', angle: Math.PI },
        { name: 'GATE 18 (PAVILION)', angle: (3 * Math.PI) / 2 }
    ];

    gatePositions.forEach(g => {
        const gx = Math.cos(g.angle) * 35;
        const gz = Math.sin(g.angle) * 35;

        const gatePillarGeo = new THREE.BoxGeometry(3, 10, 3);
        const gatePillarMat = new THREE.MeshPhongMaterial({ color: 0x42A5F5 });
        const p1 = new THREE.Mesh(gatePillarGeo, gatePillarMat);
        p1.position.set(gx - 2, 5, gz);
        stadiumGroup.add(p1);

        const p2 = new THREE.Mesh(gatePillarGeo, gatePillarMat);
        p2.position.set(gx + 2, 5, gz);
        stadiumGroup.add(p2);

        const archGeo = new THREE.BoxGeometry(7, 2, 3);
        const arch = new THREE.Mesh(archGeo, gatePillarMat);
        arch.position.set(gx, 10, gz);
        stadiumGroup.add(arch);
    });

    scene3D.add(stadiumGroup);
}

// Architectural Urban Grid with Lane Markings
function build3DRoadsAndArchitecturalGrid() {
    const roadMat = new THREE.MeshBasicMaterial({ color: 0x262a36 });
    const laneMat = new THREE.MeshBasicMaterial({ color: 0x555555 });
    const centerMat = new THREE.MeshBasicMaterial({ color: 0xc4a265 });

    // Road 1: East-West Arterial (MG Road) at z = 50, width = 20 (z: 40 to 60)
    const road1 = new THREE.Mesh(new THREE.PlaneGeometry(450, 20), roadMat);
    road1.rotation.x = -Math.PI / 2;
    road1.position.set(0, 0.1, 50);
    scene3D.add(road1);

    // MG Road lane markings — center divider + lane dashes
    const mgCenter = new THREE.Mesh(new THREE.PlaneGeometry(450, 0.4), centerMat);
    mgCenter.rotation.x = -Math.PI / 2;
    mgCenter.position.set(0, 0.15, 50);
    scene3D.add(mgCenter);
    for (let d = -220; d < 220; d += 12) {
        const dash = new THREE.Mesh(new THREE.PlaneGeometry(5, 0.25), laneMat);
        dash.rotation.x = -Math.PI / 2;
        dash.position.set(d, 0.15, 46);
        scene3D.add(dash);
        const dash2 = new THREE.Mesh(new THREE.PlaneGeometry(5, 0.25), laneMat);
        dash2.rotation.x = -Math.PI / 2;
        dash2.position.set(d, 0.15, 54);
        scene3D.add(dash2);
    }

    // Road 2: North-South Arterial (Cubbon Road) at x = 50, width = 20 (x: 40 to 60)
    const road2 = new THREE.Mesh(new THREE.PlaneGeometry(20, 450), roadMat);
    road2.rotation.x = -Math.PI / 2;
    road2.position.set(50, 0.1, 0);
    scene3D.add(road2);

    // Cubbon Road lane markings
    const cbCenter = new THREE.Mesh(new THREE.PlaneGeometry(0.4, 450), centerMat);
    cbCenter.rotation.x = -Math.PI / 2;
    cbCenter.position.set(50, 0.15, 0);
    scene3D.add(cbCenter);
    for (let d = -220; d < 220; d += 12) {
        const dash = new THREE.Mesh(new THREE.PlaneGeometry(0.25, 5), laneMat);
        dash.rotation.x = -Math.PI / 2;
        dash.position.set(46, 0.15, d);
        scene3D.add(dash);
        const dash2 = new THREE.Mesh(new THREE.PlaneGeometry(0.25, 5), laneMat);
        dash2.rotation.x = -Math.PI / 2;
        dash2.position.set(54, 0.15, d);
        scene3D.add(dash2);
    }

    // Road 3: North Cross Arterial (Infantry Road) at z = -60, width = 16 (z: -68 to -52)
    const road3 = new THREE.Mesh(new THREE.PlaneGeometry(450, 16), roadMat);
    road3.rotation.x = -Math.PI / 2;
    road3.position.set(0, 0.1, -60);
    scene3D.add(road3);

    // Infantry Road center line
    const irCenter = new THREE.Mesh(new THREE.PlaneGeometry(450, 0.3), centerMat);
    irCenter.rotation.x = -Math.PI / 2;
    irCenter.position.set(0, 0.15, -60);
    scene3D.add(irCenter);

    // Road 4: West Cross Arterial (Kasturba Road) at x = -60, width = 16 (x: -68 to -52)
    const road4 = new THREE.Mesh(new THREE.PlaneGeometry(16, 450), roadMat);
    road4.rotation.x = -Math.PI / 2;
    road4.position.set(-60, 0.1, 0);
    scene3D.add(road4);

    // Kasturba Road center line
    const krCenter = new THREE.Mesh(new THREE.PlaneGeometry(0.3, 450), centerMat);
    krCenter.rotation.x = -Math.PI / 2;
    krCenter.position.set(-60, 0.15, 0);
    scene3D.add(krCenter);

    // Architectural Building Palette
    const bMats = [
        new THREE.MeshPhongMaterial({ color: 0x181b24, flatShading: true }),
        new THREE.MeshPhongMaterial({ color: 0x1f2430, flatShading: true }),
        new THREE.MeshPhongMaterial({ color: 0x252b3b, flatShading: true }),
        new THREE.MeshPhongMaterial({ color: 0x1a212d, flatShading: true })
    ];

    function isRoadOrStadiumOverlap(bx, bz, bw, bd) {
        const halfW = bw / 2 + 5;
        const halfD = bd / 2 + 5;

        // Stadium exclusion
        const maxDist = Math.sqrt(bx * bx + bz * bz) + Math.sqrt(halfW * halfW + halfD * halfD);
        if (maxDist < 58) return true;

        // Road exclusions with buffer
        if (bx + halfW >= 36 && bx - halfW <= 64) return true;  // Cubbon Rd
        if (bx + halfW >= -72 && bx - halfW <= -48) return true; // Kasturba Rd
        if (bz + halfD >= 36 && bz - halfD <= 64) return true;  // MG Rd
        if (bz + halfD >= -72 && bz - halfD <= -48) return true; // Infantry Rd

        // Bus exclusion zones
        if (Math.hypot(bx - (-42), bz - 8) < 22) return true;  // RCB bus
        if (Math.hypot(bx - 42, bz - (-8)) < 22) return true;  // CSK bus

        return false;
    }

    const blocks = [
        { xMin: -190, xMax: -75, zMin: -190, zMax: -75 },
        { xMin: -45, xMax: 35, zMin: -190, zMax: -75 },
        { xMin: 68, xMax: 190, zMin: -190, zMax: -75 },
        { xMin: -190, xMax: -75, zMin: -45, zMax: 35 },
        { xMin: 68, xMax: 190, zMin: -45, zMax: 35 },
        { xMin: -190, xMax: -75, zMin: 68, zMax: 190 },
        { xMin: -45, xMax: 35, zMin: 68, zMax: 190 },
        { xMin: 68, xMax: 190, zMin: 68, zMax: 190 }
    ];

    blocks.forEach(block => {
        for (let i = 0; i < 5; i++) {
            const w = 12 + Math.random() * 16;
            const d = 12 + Math.random() * 16;
            const h = 16 + Math.random() * 38;

            const bx = block.xMin + Math.random() * (block.xMax - block.xMin);
            const bz = block.zMin + Math.random() * (block.zMax - block.zMin);

            if (!isRoadOrStadiumOverlap(bx, bz, w, d)) {
                const bMat = bMats[Math.floor(Math.random() * bMats.length)];
                const bGeo = new THREE.BoxGeometry(w, h, d);
                const building = new THREE.Mesh(bGeo, bMat);
                building.position.set(bx, h / 2, bz);
                scene3D.add(building);

                if (h > 30) {
                    const capGeo = new THREE.BoxGeometry(w * 0.7, 3, d * 0.7);
                    const capMat = new THREE.MeshPhongMaterial({ color: 0xc4a265 });
                    const cap = new THREE.Mesh(capGeo, capMat);
                    cap.position.set(bx, h + 1.5, bz);
                    scene3D.add(cap);
                }
            }
        }
    });
}

// Cubbon Park Trees & Landscaping — Strict exclusion around roads, buses, gates, stadium
function build3DTreesAndLandscaping() {
    const treeGroup = new THREE.Group();
    const trunkMat = new THREE.MeshPhongMaterial({ color: 0x5d4037 });
    const foliageMat1 = new THREE.MeshPhongMaterial({ color: 0x2e7d32, flatShading: true });
    const foliageMat2 = new THREE.MeshPhongMaterial({ color: 0x1b5e20, flatShading: true });

    function isTreeSafe(tx, tz) {
        // Stadium exclusion
        if (Math.hypot(tx, tz) < 48) return false;

        // Road exclusions (wider buffer)
        if (Math.abs(tx - 50) < 16) return false;   // Cubbon Road
        if (Math.abs(tx + 60) < 14) return false;   // Kasturba Road
        if (Math.abs(tz - 50) < 16) return false;   // MG Road
        if (Math.abs(tz + 60) < 14) return false;   // Infantry Road

        // Bus exclusion (generous radius)
        if (Math.hypot(tx + 42, tz - 8) < 22) return false;   // RCB bus
        if (Math.hypot(tx - 42, tz + 8) < 22) return false;   // CSK bus

        // Gate plaza exclusions (each gate extends outward)
        if (Math.abs(tx) < 8 && Math.abs(tz) < 42) return false;
        if (Math.abs(tz) < 8 && Math.abs(tx) < 42) return false;

        return true;
    }

    // Scatter trees in landscaping zones between roads
    const treeZones = [
        { xMin: -45, xMax: 35, zMin: -45, zMax: 35 },     // Inner ring around stadium
        { xMin: 65, xMax: 180, zMin: -45, zMax: 35 },     // East blocks
        { xMin: -180, xMax: -75, zMin: -45, zMax: 35 },   // West blocks
        { xMin: -45, xMax: 35, zMin: 65, zMax: 180 },     // South blocks
        { xMin: -45, xMax: 35, zMin: -180, zMax: -75 },   // North blocks
    ];

    let placed = 0;
    let attempts = 0;
    while (placed < 55 && attempts < 400) {
        attempts++;
        const zone = treeZones[Math.floor(Math.random() * treeZones.length)];
        const tx = zone.xMin + Math.random() * (zone.xMax - zone.xMin);
        const tz = zone.zMin + Math.random() * (zone.zMax - zone.zMin);

        if (!isTreeSafe(tx, tz)) continue;

        const trunkH = 4 + Math.random() * 3;
        const trunkGeo = new THREE.CylinderGeometry(0.5, 0.7, trunkH, 8);
        const trunk = new THREE.Mesh(trunkGeo, trunkMat);
        trunk.position.set(tx, trunkH / 2, tz);
        treeGroup.add(trunk);

        const folMat = placed % 2 === 0 ? foliageMat1 : foliageMat2;
        const radius = 3 + Math.random() * 1.5;
        const folGeo = new THREE.SphereGeometry(radius, 8, 8);
        const foliage = new THREE.Mesh(folGeo, folMat);
        foliage.position.set(tx, trunkH + radius * 0.6, tz);
        treeGroup.add(foliage);

        // Secondary canopy for larger trees
        if (Math.random() > 0.5) {
            const fol2Geo = new THREE.SphereGeometry(radius * 0.7, 8, 8);
            const fol2 = new THREE.Mesh(fol2Geo, foliageMat2);
            fol2.position.set(tx + 1.2, trunkH + radius * 0.3, tz + 0.8);
            treeGroup.add(fol2);
        }

        placed++;
    }
    scene3D.add(treeGroup);
}

// Bengaluru Potholes on Bottleneck Junctions & Road Stretches
function build3DPotholes() {
    const potholeMat = new THREE.MeshBasicMaterial({ color: 0x050505, side: THREE.DoubleSide });
    const rimMat = new THREE.MeshBasicMaterial({ color: 0x1a1a1a, side: THREE.DoubleSide });

    const locations = [
        { x: 50, z: 42 }, { x: 54, z: -55 }, { x: -55, z: 48 }, { x: 48, z: 54 },
        { x: 46, z: 80 }, { x: 54, z: -120 }, { x: -60, z: -80 }, { x: 120, z: 50 },
        { x: -100, z: 46 }, { x: 50, z: -30 }
    ];

    locations.forEach(loc => {
        // Outer rim
        const rimGeo = new THREE.RingGeometry(2.5, 3.8, 16);
        const rim = new THREE.Mesh(rimGeo, rimMat);
        rim.rotation.x = -Math.PI / 2;
        rim.position.set(loc.x, 0.16, loc.z);
        scene3D.add(rim);

        // Inner hole
        const holeGeo = new THREE.RingGeometry(0.6, 2.5, 16);
        const hole = new THREE.Mesh(holeGeo, potholeMat);
        hole.rotation.x = -Math.PI / 2;
        hole.position.set(loc.x, 0.18, loc.z);
        scene3D.add(hole);
    });
}

// 🚌 RCB & CSK IPL Team Luxury Buses
function build3DTeamBuses() {
    // 1. RCB Team Bus (Red & Gold) near Gate 12 VIP Entrance (x: -42, z: 8)
    const rcbBus = new THREE.Group();
    const rcbMat = new THREE.MeshPhongMaterial({ color: 0xd32f2f }); // RCB Red
    const goldMat = new THREE.MeshPhongMaterial({ color: 0xffd700 });
    const darkMat = new THREE.MeshPhongMaterial({ color: 0x111111 });

    const bodyGeo = new THREE.BoxGeometry(4.5, 3.2, 14);
    const body = new THREE.Mesh(bodyGeo, rcbMat);
    body.position.y = 2.2;
    rcbBus.add(body);

    const stripeGeo = new THREE.BoxGeometry(4.6, 0.6, 14.1);
    const stripe = new THREE.Mesh(stripeGeo, goldMat);
    stripe.position.y = 2.2;
    rcbBus.add(stripe);

    const winGeo = new THREE.BoxGeometry(4.7, 1.2, 11);
    const win = new THREE.Mesh(winGeo, darkMat);
    win.position.y = 2.8;
    rcbBus.add(win);

    rcbBus.position.set(-42, 0, 8);
    rcbBus.rotation.y = Math.PI / 6;
    scene3D.add(rcbBus);

    // 2. CSK Team Bus (Canary Yellow) near Gate 1 Main Entrance (x: 42, z: -8)
    const cskBus = new THREE.Group();
    const cskMat = new THREE.MeshPhongMaterial({ color: 0xfbc02d }); // CSK Yellow

    const cBody = new THREE.Mesh(bodyGeo, cskMat);
    cBody.position.y = 2.2;
    cskBus.add(cBody);

    const cWin = new THREE.Mesh(winGeo, darkMat);
    cWin.position.y = 2.8;
    cskBus.add(cWin);

    cskBus.position.set(42, 0, -8);
    cskBus.rotation.y = -Math.PI / 4;
    scene3D.add(cskBus);
}

// 🚧 High Security Police Barricades
function build3DPoliceBarricades() {
    const barMat = new THREE.MeshPhongMaterial({ color: 0xfbc02d }); // Police Yellow
    const stripeMat = new THREE.MeshPhongMaterial({ color: 0x111111 });

    const gates = [
        { x: 38, z: 0, rot: Math.PI / 2 },
        { x: -38, z: 0, rot: Math.PI / 2 },
        { x: 0, z: 38, rot: 0 },
        { x: 0, z: -38, rot: 0 },
        { x: 50, z: 38, rot: 0 } // MG Rd Junction checkpoint
    ];

    gates.forEach(g => {
        const barGroup = new THREE.Group();

        const barGeo = new THREE.BoxGeometry(8, 2.5, 0.8);
        const bar = new THREE.Mesh(barGeo, barMat);
        bar.position.y = 1.8;
        barGroup.add(bar);

        const stripeGeo = new THREE.BoxGeometry(2, 2.6, 0.9);
        const st1 = new THREE.Mesh(stripeGeo, stripeMat);
        st1.position.set(-2, 1.8, 0);
        barGroup.add(st1);

        const st2 = new THREE.Mesh(stripeGeo, stripeMat);
        st2.position.set(2, 1.8, 0);
        barGroup.add(st2);

        barGroup.position.set(g.x, 0, g.z);
        barGroup.rotation.y = g.rot;
        barricadesGroup.add(barGroup);
    });
}

// Fan Crowd & Gate Entry Queues — Arc-curved along concourse, zero road crossing
function build3DFansAndCrowd() {
    const rcbJerseyMat = new THREE.MeshPhongMaterial({ color: 0xd32f2f });
    const cskJerseyMat = new THREE.MeshPhongMaterial({ color: 0xfbc02d });
    const skinMat = new THREE.MeshPhongMaterial({ color: 0xd4b275 });
    const pantsMat = new THREE.MeshPhongMaterial({ color: 0x1f2430 });

    function createFanMesh(isRCB) {
        const fanGroup = new THREE.Group();
        const jerseyMat = isRCB ? rcbJerseyMat : cskJerseyMat;

        const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.7, 2.2, 8), jerseyMat);
        torso.position.y = 2.1;
        fanGroup.add(torso);

        const legs = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.5, 2, 8), pantsMat);
        legs.position.y = 1;
        fanGroup.add(legs);

        const head = new THREE.Mesh(new THREE.SphereGeometry(0.6, 10, 10), skinMat);
        head.position.y = 3.5;
        fanGroup.add(head);

        return fanGroup;
    }

    function isFanSafe(fx, fz) {
        // Never on roads
        if (Math.abs(fx - 50) < 14) return false;  // Cubbon Road
        if (Math.abs(fx + 60) < 12) return false;  // Kasturba Road
        if (Math.abs(fz - 50) < 14) return false;  // MG Road
        if (Math.abs(fz + 60) < 12) return false;  // Infantry Road
        return true;
    }

    // Gate Queues: TRUE ARC along concourse circle (radius 37)
    // Each gate starts at a specific angle on the circle and fans arc along it
    const gateQueues = [
        { gateAngle: 0, arcDir: -1, count: 22 },                    // Gate 1 (East) — arcs clockwise (south)
        { gateAngle: Math.PI / 2, arcDir: -1, count: 18 },          // Gate 2 (South) — arcs clockwise (east)
        { gateAngle: Math.PI, arcDir: 1, count: 20 },               // Gate 12 (West) — arcs counter-clockwise (south)
        { gateAngle: 3 * Math.PI / 2, arcDir: 1, count: 16 }       // Gate 18 (North) — arcs counter-clockwise (east)
    ];

    const queueRadius = 37;
    const fanSpacing = 0.045; // radians between fans in queue

    gateQueues.forEach(gq => {
        for (let i = 0; i < gq.count; i++) {
            const angle = gq.gateAngle + gq.arcDir * fanSpacing * i;
            const jitter = (Math.random() - 0.5) * 1.2;
            const r = queueRadius + jitter;
            const fx = Math.cos(angle) * r;
            const fz = Math.sin(angle) * r;

            if (!isFanSafe(fx, fz)) continue;

            const fan = createFanMesh(i % 2 === 0);
            fan.position.set(fx, 0, fz);
            // Face toward stadium center
            fan.rotation.y = angle + Math.PI;
            crowdParticlesGroup.add(fan);
        }
    });

    // Dense Stadium Concourse Spectators (fans milling around on concourse radius 36-42)
    let placed = 0;
    let attempts = 0;
    while (placed < 180 && attempts < 600) {
        attempts++;
        const angle = Math.random() * Math.PI * 2;
        const dist = 36 + Math.random() * 6;
        const fx = Math.cos(angle) * dist;
        const fz = Math.sin(angle) * dist;

        if (!isFanSafe(fx, fz)) continue;

        const fan = createFanMesh(placed % 3 !== 0); // ~2/3 RCB fans (home team)
        fan.position.set(fx, 0, fz);
        fan.rotation.y = Math.random() * Math.PI * 2;
        crowdParticlesGroup.add(fan);
        placed++;
    }
}

// 2-Way Road Traffic with Realistic Barricade Stop Physics
function build3DTwoWayVehiclesAndBikes() {
    const carMatRed = new THREE.MeshPhongMaterial({ color: 0xe84040 });
    const carMatWhite = new THREE.MeshPhongMaterial({ color: 0xf0eef4 });
    const carMatBlue = new THREE.MeshPhongMaterial({ color: 0x42A5F5 });
    const carMatSilver = new THREE.MeshPhongMaterial({ color: 0x9e9e9e });
    const bikeMatYellow = new THREE.MeshPhongMaterial({ color: 0xfbc02d });
    const bikeMatBlack = new THREE.MeshPhongMaterial({ color: 0x111111 });
    const bikeMatOrange = new THREE.MeshPhongMaterial({ color: 0xff6d00 });
    const cabinMat = new THREE.MeshPhongMaterial({ color: 0x111111 });
    const brakeLightMat = new THREE.MeshBasicMaterial({ color: 0xff0000 });

    const carMats = [carMatRed, carMatWhite, carMatBlue, carMatSilver];
    const bikeMats = [bikeMatYellow, bikeMatBlack, bikeMatOrange];

    // Helper: create a car mesh
    function makeCar(mat, axis) {
        const carGroup = new THREE.Group();
        if (axis === 'z') {
            const body = new THREE.Mesh(new THREE.BoxGeometry(3.2, 1.4, 6), mat);
            body.position.y = 1;
            carGroup.add(body);
            const cabin = new THREE.Mesh(new THREE.BoxGeometry(2.6, 1.2, 3), cabinMat);
            cabin.position.set(0, 2.1, -0.2);
            carGroup.add(cabin);
        } else {
            const body = new THREE.Mesh(new THREE.BoxGeometry(6, 1.4, 3.2), mat);
            body.position.y = 1;
            carGroup.add(body);
            const cabin = new THREE.Mesh(new THREE.BoxGeometry(3, 1.2, 2.6), cabinMat);
            cabin.position.set(-0.2, 2.1, 0);
            carGroup.add(cabin);
        }
        return carGroup;
    }

    // Helper: create a bike mesh
    function makeBike(mat) {
        const bikeGroup = new THREE.Group();
        const bBody = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1, 3), mat);
        bBody.position.y = 0.8;
        bikeGroup.add(bBody);
        const riderBody = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.4, 1.4, 8), new THREE.MeshPhongMaterial({ color: 0x333333 }));
        riderBody.position.set(0, 1.8, 0);
        bikeGroup.add(riderBody);
        const riderHead = new THREE.Mesh(new THREE.SphereGeometry(0.4, 8, 8), bikeMatBlack);
        riderHead.position.set(0, 2.8, 0);
        bikeGroup.add(riderHead);
        return bikeGroup;
    }

    // 1. Cubbon Road (x = 50): Northbound lane x=54, Southbound lane x=46
    for (let i = 0; i < 14; i++) {
        const isNorthbound = i % 2 === 0;
        const laneX = isNorthbound ? 54 : 46;
        const zPos = -180 + i * 30;

        if (i % 4 === 0) {
            const bike = makeBike(bikeMats[i % bikeMats.length]);
            bike.position.set(laneX, 0, zPos);
            bike.rotation.y = isNorthbound ? 0 : Math.PI;
            bike.userData = { roadAxis: 'z', isNorthbound, laneX, speed: 0.14 };
            bikesGroup.add(bike);
        } else {
            const car = makeCar(carMats[i % carMats.length], 'z');
            car.position.set(laneX, 0, zPos);
            car.rotation.y = isNorthbound ? 0 : Math.PI;
            car.userData = { roadAxis: 'z', isNorthbound, laneX, speed: 0.10 + Math.random() * 0.02 };
            carsGroup.add(car);
        }
    }

    // 2. MG Road (z = 50): Eastbound lane z=54, Westbound lane z=46
    for (let i = 0; i < 14; i++) {
        const isEastbound = i % 2 === 0;
        const laneZ = isEastbound ? 54 : 46;
        const xPos = -180 + i * 30;

        if (i % 5 === 0) {
            const bike = makeBike(bikeMats[i % bikeMats.length]);
            bike.position.set(xPos, 0, laneZ);
            bike.rotation.y = isEastbound ? -Math.PI / 2 : Math.PI / 2;
            bike.userData = { roadAxis: 'x', isEastbound, laneZ, speed: 0.14 };
            bikesGroup.add(bike);
        } else {
            const car = makeCar(carMats[i % carMats.length], 'x');
            car.position.set(xPos, 0, laneZ);
            car.rotation.y = isEastbound ? 0 : Math.PI;
            car.userData = { roadAxis: 'x', isEastbound, laneZ, speed: 0.10 + Math.random() * 0.02 };
            carsGroup.add(car);
        }
    }

    // 3. Infantry Road (z = -60): Eastbound lane z=-56, Westbound lane z=-64
    for (let i = 0; i < 8; i++) {
        const isEastbound = i % 2 === 0;
        const laneZ = isEastbound ? -56 : -64;
        const xPos = -160 + i * 40;

        const car = makeCar(carMats[i % carMats.length], 'x');
        car.position.set(xPos, 0, laneZ);
        car.rotation.y = isEastbound ? 0 : Math.PI;
        car.userData = { roadAxis: 'x', isEastbound, laneZ, speed: 0.10 + Math.random() * 0.02 };
        carsGroup.add(car);
    }

    // 4. Kasturba Road (x = -60): Northbound lane x=-56, Southbound lane x=-64
    for (let i = 0; i < 8; i++) {
        const isNorthbound = i % 2 === 0;
        const laneX = isNorthbound ? -56 : -64;
        const zPos = -160 + i * 40;

        const car = makeCar(carMats[i % carMats.length], 'z');
        car.position.set(laneX, 0, zPos);
        car.rotation.y = isNorthbound ? 0 : Math.PI;
        car.userData = { roadAxis: 'z', isNorthbound, laneX, speed: 0.10 + Math.random() * 0.02 };
        carsGroup.add(car);
    }

    // 5. Barricaded Junction Traffic Jam Queue (bumper-to-bumper BEHIND barricade on Cubbon Rd)
    // Barricade is at z=38, so jam cars queue southward from z=35 down
    for (let j = 0; j < 6; j++) {
        const jamCar = makeCar(j % 2 === 0 ? carMatRed : carMatBlue, 'z');

        // Brake lights
        const bLight1 = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.4, 0.2), brakeLightMat);
        bLight1.position.set(-1, 1.2, -3.1);
        jamCar.add(bLight1);
        const bLight2 = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.4, 0.2), brakeLightMat);
        bLight2.position.set(1, 1.2, -3.1);
        jamCar.add(bLight2);

        // Queue BEHIND barricade: z = 35 down to z = -7 (northbound lane x=54)
        jamCar.position.set(54, 0, 35 - j * 9);
        jamCar.userData = { isStuck: true, roadAxis: 'z', isNorthbound: true, laneX: 54 };
        carsGroup.add(jamCar);
    }

    // 6. Jam queue on MG Road approaching junction (westbound lane z=46)
    // Junction box ends at x=62, so jam starts at x=65 outward
    for (let j = 0; j < 4; j++) {
        const jamCar = makeCar(j % 2 === 0 ? carMatSilver : carMatRed, 'x');

        const bL1 = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.4, 0.8), brakeLightMat);
        bL1.position.set(-3.1, 1.2, -1);
        jamCar.add(bL1);
        const bL2 = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.4, 0.8), brakeLightMat);
        bL2.position.set(-3.1, 1.2, 1);
        jamCar.add(bL2);

        // Queue eastward from x=68 (clear of junction box x: 38-62)
        jamCar.position.set(68 + j * 10, 0, 46);
        jamCar.rotation.y = Math.PI;
        jamCar.userData = { isStuck: true, roadAxis: 'x', isEastbound: false, laneZ: 46 };
        carsGroup.add(jamCar);
    }
}

// 👮 Police Constables Standing Behind Barricades
function build3DPoliceConstables() {
    const policeMat = new THREE.MeshPhongMaterial({ color: 0xAB47BC });
    const capMat = new THREE.MeshPhongMaterial({ color: 0x111111 });

    const pos = [
        { x: 38, z: 3 }, { x: -38, z: 3 }, { x: 3, z: 38 }, { x: 3, z: -38 }, { x: 50, z: 42 }
    ];

    pos.forEach(p => {
        const cGroup = new THREE.Group();

        const bodyGeo = new THREE.CylinderGeometry(0.8, 1, 4, 8);
        const body = new THREE.Mesh(bodyGeo, policeMat);
        body.position.y = 2;
        cGroup.add(body);

        const headGeo = new THREE.SphereGeometry(0.9, 12, 12);
        const headMat = new THREE.MeshPhongMaterial({ color: 0xd4b275 });
        const head = new THREE.Mesh(headGeo, headMat);
        head.position.y = 4.4;
        cGroup.add(head);

        const capGeo = new THREE.CylinderGeometry(1.2, 1, 0.4, 12);
        const cap = new THREE.Mesh(capGeo, capMat);
        cap.position.y = 5.2;
        cGroup.add(cap);

        cGroup.position.set(p.x, 0, p.z);
        constablesGroup.add(cGroup);
    });
}

function update3DBeacons(data) {
    if (!scene3D || !junctionBeaconsGroup) return;

    while (junctionBeaconsGroup.children.length > 0) {
        const obj = junctionBeaconsGroup.children[0];
        junctionBeaconsGroup.remove(obj);
    }

    const junctions = data.impact.junction_impacts;
    if (!junctions) return;

    junctions.forEach((j, idx) => {
        const angle = (idx / junctions.length) * Math.PI * 2;
        const dist = 75 + (j.distance_km * 28);
        const x = Math.cos(angle) * dist;
        const z = Math.sin(angle) * dist;

        const h = j.severity === 'CRITICAL' ? 48 : j.severity === 'HIGH' ? 32 : 20;
        const colorHex = j.severity === 'CRITICAL' ? 0xe84040 : j.severity === 'HIGH' ? 0xe8a838 : 0xc4a265;

        const cylinderGeo = new THREE.CylinderGeometry(2.5, 2.5, h, 16);
        const cylinderMat = new THREE.MeshPhongMaterial({
            color: colorHex,
            transparent: true,
            opacity: 0.78,
            emissive: colorHex,
            emissiveIntensity: 0.4,
        });
        const beacon = new THREE.Mesh(cylinderGeo, cylinderMat);
        beacon.position.set(x, h / 2, z);
        junctionBeaconsGroup.add(beacon);

        const sphereGeo = new THREE.SphereGeometry(4.2, 16, 16);
        const sphereMat = new THREE.MeshBasicMaterial({ color: colorHex });
        const sphere = new THREE.Mesh(sphereGeo, sphereMat);
        sphere.position.set(x, h + 2, z);
        junctionBeaconsGroup.add(sphere);
    });
}

function animate3DScene() {
    animationFrameId3D = requestAnimationFrame(animate3DScene);

    if (controls3D) controls3D.update();

    // ──── Intersection crossing management ────
    // Cubbon Rd × MG Rd junction box: x ∈ [36, 64], z ∈ [36, 64]
    // Use a 4-second cycle: first 2s → z-axis (Cubbon Rd) has green, next 2s → x-axis (MG Rd) has green
    const junctionCycleMs = 4000;
    const cyclePhase = (Date.now() % junctionCycleMs) / junctionCycleMs;
    const zAxisHasGreen = cyclePhase < 0.5; // First half: Cubbon Rd goes, second half: MG Rd goes

    // Junction box boundaries
    const JX_MIN = 36, JX_MAX = 64, JZ_MIN = 36, JZ_MAX = 64;

    function isInJunction(x, z) {
        return x > JX_MIN && x < JX_MAX && z > JZ_MIN && z < JZ_MAX;
    }

    // ──── Barricade stop zones ────
    function shouldStopOnZ(z, isNorthbound, laneX) {
        if (isNorthbound && z > 30 && z < 38 && Math.abs(laneX - 50) < 12) return true;
        if (!isNorthbound && z < -30 && z > -38) return true;
        return false;
    }

    function shouldStopOnX(x, isEastbound, laneZ) {
        if (isEastbound && x > 30 && x < 38) return true;
        if (!isEastbound && x < -30 && x > -38) return true;
        if (isEastbound && x > 42 && x < 50 && Math.abs(laneZ - 50) < 12) return true;
        return false;
    }

    // ──── Following-distance helper ────
    // Checks all vehicles (cars + bikes + jam) for same-lane proximity ahead
    function getVehicleAhead(vehicle, allVehicles) {
        const ud = vehicle.userData;
        if (!ud || !ud.roadAxis) return false;

        const MIN_GAP = 12; // minimum following distance (car length ~6 + buffer)

        for (let i = 0; i < allVehicles.length; i++) {
            const other = allVehicles[i];
            if (other === vehicle) continue;

            // Check proximity based on POSITION regardless of other vehicle's metadata
            // This ensures jam cars (isStuck) and any vehicle on the lane are detected
            if (ud.roadAxis === 'z') {
                // Is 'other' on the same vertical lane? (within 4 units of our laneX)
                if (Math.abs(vehicle.position.x - other.position.x) > 4) continue;

                const dz = other.position.z - vehicle.position.z;
                if (ud.isNorthbound && dz > 0 && dz < MIN_GAP) return true;
                if (!ud.isNorthbound && dz < 0 && -dz < MIN_GAP) return true;

            } else if (ud.roadAxis === 'x') {
                // Is 'other' on the same horizontal lane? (within 4 units of our laneZ)
                if (Math.abs(vehicle.position.z - other.position.z) > 4) continue;

                const dx = other.position.x - vehicle.position.x;
                if (ud.isEastbound && dx > 0 && dx < MIN_GAP) return true;
                if (!ud.isEastbound && dx < 0 && -dx < MIN_GAP) return true;
            }
        }

        return false;
    }

    // Build combined vehicle list once per frame
    const allMovingVehicles = [];
    if (carsGroup) carsGroup.children.forEach(c => allMovingVehicles.push(c));
    if (bikesGroup) bikesGroup.children.forEach(b => allMovingVehicles.push(b));

    // ──── Animate Cars ────
    if (carsGroup && showParticles3D) {
        carsGroup.children.forEach(car => {
            if (!car.userData || car.userData.isStuck) return;

            if (car.userData.roadAxis === 'z') {
                car.position.x = car.userData.laneX;

                // Barricade stop
                if (shouldStopOnZ(car.position.z, car.userData.isNorthbound, car.userData.laneX)) return;

                // Intersection crossing: z-axis vehicles wait when MG Rd has green
                const nextZ = car.position.z + (car.userData.isNorthbound ? 1 : -1) * 3;
                if (!zAxisHasGreen && isInJunction(car.position.x, nextZ) && !isInJunction(car.position.x, car.position.z)) {
                    return; // Wait at intersection edge
                }

                // Following distance: don't advance if vehicle ahead is too close
                if (getVehicleAhead(car, allMovingVehicles)) return;

                const dir = car.userData.isNorthbound ? 1 : -1;
                car.position.z += dir * car.userData.speed;

                if (car.position.z > 200) car.position.z = -200;
                if (car.position.z < -200) car.position.z = 200;

            } else if (car.userData.roadAxis === 'x') {
                car.position.z = car.userData.laneZ;

                if (shouldStopOnX(car.position.x, car.userData.isEastbound, car.userData.laneZ)) return;

                // Intersection crossing: x-axis vehicles wait when Cubbon Rd has green
                const nextX = car.position.x + (car.userData.isEastbound ? 1 : -1) * 3;
                if (zAxisHasGreen && isInJunction(nextX, car.position.z) && !isInJunction(car.position.x, car.position.z)) {
                    return;
                }

                if (getVehicleAhead(car, allMovingVehicles)) return;

                const dir = car.userData.isEastbound ? 1 : -1;
                car.position.x += dir * car.userData.speed;

                if (car.position.x > 200) car.position.x = -200;
                if (car.position.x < -200) car.position.x = 200;
            }
        });
    }

    // ──── Animate Bikes ────
    if (bikesGroup && showParticles3D) {
        bikesGroup.children.forEach(bike => {
            if (!bike.userData) return;

            if (bike.userData.roadAxis === 'z') {
                bike.position.x = bike.userData.laneX;

                if (shouldStopOnZ(bike.position.z, bike.userData.isNorthbound, bike.userData.laneX)) return;

                const nextZ = bike.position.z + (bike.userData.isNorthbound ? 1 : -1) * 3;
                if (!zAxisHasGreen && isInJunction(bike.position.x, nextZ) && !isInJunction(bike.position.x, bike.position.z)) return;

                if (getVehicleAhead(bike, allMovingVehicles)) return;

                const dir = bike.userData.isNorthbound ? 1 : -1;
                bike.position.z += dir * bike.userData.speed;
                if (bike.position.z > 200) bike.position.z = -200;
                if (bike.position.z < -200) bike.position.z = 200;

            } else if (bike.userData.roadAxis === 'x') {
                bike.position.z = bike.userData.laneZ;

                if (shouldStopOnX(bike.position.x, bike.userData.isEastbound, bike.userData.laneZ)) return;

                const nextX = bike.position.x + (bike.userData.isEastbound ? 1 : -1) * 3;
                if (zAxisHasGreen && isInJunction(nextX, bike.position.z) && !isInJunction(bike.position.x, bike.position.z)) return;

                if (getVehicleAhead(bike, allMovingVehicles)) return;

                const dir = bike.userData.isEastbound ? 1 : -1;
                bike.position.x += dir * bike.userData.speed;
                if (bike.position.x > 200) bike.position.x = -200;
                if (bike.position.x < -200) bike.position.x = 200;
            }
        });
    }

    // Gentle waving animation for fan crowd
    if (crowdParticlesGroup && showParticles3D) {
        crowdParticlesGroup.children.forEach((fan, idx) => {
            if (fan.position) {
                fan.position.y = Math.sin(Date.now() * 0.004 + idx * 0.5) * 0.12;
            }
        });
    }

    // Rotating beacon pillars
    if (junctionBeaconsGroup && showBeacons3D) {
        junctionBeaconsGroup.rotation.y += 0.002;
    }

    if (renderer3D && scene3D && camera3D) {
        renderer3D.render(scene3D, camera3D);
    }
}

function on3DWindowResize() {
    const container = document.getElementById('tactical3DCanvas');
    if (!container || !renderer3D || !camera3D) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 500;

    camera3D.aspect = width / height;
    camera3D.updateProjectionMatrix();
    renderer3D.setSize(width, height);
}

function reset3DCamera() {
    if (camera3D && controls3D) {
        camera3D.position.set(0, 170, 230);
        controls3D.target.set(0, 0, 0);
        controls3D.update();
    }
}

function toggle3DTrafficParticles() {
    showParticles3D = !showParticles3D;
    if (carsGroup) carsGroup.visible = showParticles3D;
    if (bikesGroup) bikesGroup.visible = showParticles3D;
    if (crowdParticlesGroup) crowdParticlesGroup.visible = showParticles3D;
}

function toggle3DPulsingBeacons() {
    showBeacons3D = !showBeacons3D;
    if (junctionBeaconsGroup) junctionBeaconsGroup.visible = showBeacons3D;
}

// Spotlight & Details
function initSpotlight() {
    document.getElementById('spotlightClose').addEventListener('click', closeSpotlight);
}

// App Initialization
document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('eventDate');
    const today = new Date();
    today.setDate(today.getDate() + 6);
    dateInput.value = today.toISOString().split('T')[0];

    initTheme();
    startClock();
    initViews();
    initKeyboardShortcuts();
    initFilterChips();
    initHistory();
    initTableControls();
    initSpotlight();
    updateHistoryCount();

    const tickerContent = document.getElementById('tickerContent');
    const tickerTrack = document.querySelector('.ticker-track');
    if (tickerTrack) {
        tickerTrack.addEventListener('mouseenter', () => tickerContent.classList.add('paused'));
        tickerTrack.addEventListener('mouseleave', () => tickerContent.classList.remove('paused'));
    }
});
