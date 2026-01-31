const resourceGpu = document.getElementById('resource-gpu');
const resourceWindows = document.getElementById('resource-windows');
const summaryText = document.getElementById('memory-summary');
const summaryTimestamp = document.getElementById('memory-summary-timestamp');
const planSummary = document.getElementById('plan-summary');
const planSteps = document.getElementById('plan-steps');
const watcherEventsList = document.getElementById('watcher-events-list');
const busMetricsSummary = document.getElementById('bus-metrics-summary');
const busMetricsRecent = document.getElementById('bus-metrics-recent');
const memoryEventsList = document.getElementById('memory-events-list');

async function updateResourcePanel() {
    try {
        const resp = await fetch('/api/resource_events');
        const data = await resp.json();
        const gpu = data.summary?.gpu;
        resourceGpu.textContent = gpu ? `${(gpu * 100).toFixed(1)}%` : 'N/A';
        resourceWindows.innerHTML = '';
        if (data.summary?.windows.length) {
            data.summary.windows.forEach(win => {
                const item = document.createElement('div');
                item.className = 'resource-window';
                item.textContent = `${win.title} (${win.window_id})`;
                resourceWindows.appendChild(item);
            });
        } else {
        resourceWindows.textContent = 'No hay ventanas recientes.';
    }
        if (gpu && gpu >= 0.85 && window.updateStatus) {
            updateStatus('GPU alta, priorizando tareas ligeras.', 'warning');
        }
    } catch (err) {
        console.error('No se pudo cargar los eventos de recursos', err);
    }
}

async function updateMemorySummary() {
    try {
        const resp = await fetch('/api/memory_summary');
        const data = await resp.json();
        if (data.summary) {
            summaryText.textContent = data.summary;
            if (data.timestamp) {
                const date = new Date(data.timestamp * 1000);
                summaryTimestamp.textContent = `Último resumen: ${date.toLocaleString()}`;
            }
        } else {
            summaryText.textContent = data.note || 'Sin resumen automático aún.';
            summaryTimestamp.textContent = '';
        }
    } catch (err) {
        console.error('No se pudo cargar el resumen de memoria', err);
    }
}

setInterval(updateResourcePanel, 12_000);
setInterval(updateMemorySummary, 30_000);
setInterval(updatePlanPanel, 45_000);
setInterval(updateWatcherPanel, 25_000);
setInterval(updateBusMetricsPanel, 20_000);
setInterval(updateMemoryEventsPanel, 25_000);
updateResourcePanel();
updateMemorySummary();
updatePlanPanel();
updateWatcherPanel();
updateBusMetricsPanel();
updateMemoryEventsPanel();

const refreshMemoryBtn = document.getElementById('refresh-memory-btn');
if (refreshMemoryBtn) {
    refreshMemoryBtn.addEventListener('click', (event) => {
        event.preventDefault();
        updateMemorySummary();
    });
}

async function updatePlanPanel() {
    if (!planSummary || !planSteps) return;
    try {
        const resp = await fetch('/api/plan_log');
        const data = await resp.json();
        if (!data.plan) {
            planSummary.textContent = 'Sin plan registrado aún.';
            planSteps.innerHTML = '';
            return;
        }
        const date = new Date(data.plan.timestamp * 1000);
        planSummary.textContent = `${data.plan.prompt} (${date.toLocaleString()})`;
        planSteps.innerHTML = '';
        data.plan.steps.forEach(step => {
            const item = document.createElement('div');
            item.className = 'plan-step';
            const title = document.createElement('div');
            title.textContent = `${step.action} → ${step.target}`;
            const reason = document.createElement('div');
            reason.className = 'plan-step-rationale';
            reason.textContent = step.rationale || 'Sin justificación';
            item.appendChild(title);
            item.appendChild(reason);
            planSteps.appendChild(item);
        });
    } catch (err) {
        console.error('No se pudo cargar el plan', err);
    }
}

async function updateWatcherPanel() {
    if (!watcherEventsList) {
        return;
    }
    try {
        const resp = await fetch('/api/watcher_events');
        const data = await resp.json();
        const events = data.events || [];
        watcherEventsList.innerHTML = '';
        if (!events.length) {
            watcherEventsList.textContent = 'Sin eventos recientes.';
            return;
        }
        events.forEach(evt => {
            const item = document.createElement('div');
            item.className = 'watcher-event';
            const timeText = evt.timestamp
                ? new Date(evt.timestamp * 1000).toLocaleTimeString()
                : '—';
            const details = typeof evt.details === 'object'
                ? JSON.stringify(evt.details)
                : evt.details;
            item.innerHTML = `<strong>${timeText} · ${evt.type}</strong><div>${details}</div>`;
            watcherEventsList.appendChild(item);
        });
    } catch (err) {
        console.error('No se pudo cargar los eventos del sistema', err);
        watcherEventsList.textContent = 'Error cargando eventos.';
    }
}

async function updateBusMetricsPanel() {
    if (!busMetricsSummary || !busMetricsRecent) return;
    try {
        const resp = await fetch('/api/bus_metrics');
        if (!resp.ok) throw new Error('Bus metrics fetch failed');
        const payload = await resp.json();
        const summary = payload.summary?.summary || {};
        if (!Object.keys(summary).length) {
            busMetricsSummary.textContent = 'Sin métricas registradas todavía.';
        } else {
            busMetricsSummary.innerHTML = Object.entries(summary)
                .map(([key, stats]) => `<div><strong>${key}</strong>: última=${stats.latest} avg=${stats.avg}</div>`)
                .join('');
        }
        busMetricsRecent.innerHTML = '';
        (payload.summary?.recent || []).forEach(record => {
            const el = document.createElement('div');
            el.className = 'metrics-list-item';
            const time = new Date(record.timestamp).toLocaleTimeString();
            const metrics = record.metrics
                ? Object.entries(record.metrics)
                      .map(([k, v]) => `${k}=${v}`)
                      .join(' ')
                : 'sin detalles';
            el.textContent = `${time} · ${metrics}`;
            busMetricsRecent.appendChild(el);
        });
    } catch (err) {
        console.error('No se pudo cargar métricas del bus', err);
        if (busMetricsSummary) {
            busMetricsSummary.textContent = 'Error cargando métricas del bus.';
        }
    }
}

async function updateMemoryEventsPanel() {
    if (!memoryEventsList) return;
    try {
        const resp = await fetch('/api/memory_events');
        if (!resp.ok) throw new Error('Memory events fetch failed');
        const payload = await resp.json();
        memoryEventsList.innerHTML = '';
        if (!payload.events?.length) {
            memoryEventsList.textContent = 'Sin eventos de memoria recientes.';
            return;
        }
        payload.events.forEach(evt => {
            const el = document.createElement('div');
            el.className = 'memory-events-item';
            const timestamp = evt.timestamp || '—';
            const detailText = evt.details ? evt.details : evt.raw || '';
            el.innerHTML = `<strong>${timestamp}</strong><div>${detailText}</div>`;
            memoryEventsList.appendChild(el);
        });
    } catch (err) {
        console.error('No se pudo cargar eventos de memoria', err);
        memoryEventsList.textContent = 'Error cargando eventos de memoria.';
    }
}
