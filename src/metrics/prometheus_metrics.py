from prometheus_client import Counter, Histogram, Gauge

STAGE_LATENCY_HISTOGRAM = Histogram(
    "lucy_stage_latency_ms",
    "Latencia de cada etapa (manager → worker → respuesta)",
    buckets=[10, 50, 100, 200, 500, 1000, 2000, 5000],
)

DOM_TASKS_COUNTER = Counter(
    "lucy_dom_tasks_total",
    "Cantidad de tareas de distilación DOM procesadas (Playwright → Ray)",
)

RAY_TASKS_IN_FLIGHT = Gauge(
    "lucy_ray_tasks_in_flight",
    "Tareas Ray en ejecución para distilación DOM/planificación.",
)
