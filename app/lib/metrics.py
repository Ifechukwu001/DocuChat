from prometheus_client import Gauge, Counter, Histogram

# Counter: total number of HTTP requests
http_requests_total = Counter(
    name="docuchat_http_requests_total",
    documentation="Total HTTP requests",
    labelnames=["method", "path", "status_code"],
    namespace="docuchat_",
)

# Histogram: request duration distribution
http_request_duration = Histogram(
    name="docuchat_http_request_duration_seconds",
    documentation="HTTP request duration in seconds",
    labelnames=["method", "path"],
    namespace="docuchat_",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
)


# Counter: document processing results
document_processed = Counter(
    name="docuchat_document_processed_total",
    documentation="Documents processed by the queue worker",
    labelnames=["status"],  # "success" or "failed"
    namespace="docuchat_",
)


# Gauge: active queue jobs (goes up and down)
active_queue_jobs = Gauge(
    name="docuchat_active_queue_jobs",
    documentation="Currently active queue jobs",
    labelnames=["queue"],
    namespace="docuchat_",
)


# Counter: cache hits and misses
cache_operations = Counter(
    name="docuchat_cache_operations_total",
    documentation="Cache operations",
    labelnames=["operation", "result"],  # get/set, hit/miss
    namespace="docuchat_",
)


ingestion_duration = Histogram(
    name="docuchat_ingestion_duration_seconds",
    documentation="Document ingestion duration",
    labelnames=["format"],
    namespace="docuchat_",
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

chunks_per_document = Histogram(
    name="docuchat_chunks_per_document",
    documentation="Number of chunks generated per document",
    namespace="docuchat_",
    buckets=[5, 10, 25, 50, 100, 250, 500],
)


embedding_cache_hit_rate = Gauge(
    name="docuchat_embedding_cache_hit_rate",
    documentation="Percentage of embedding requests served from cache",
    namespace="docuchat_",
)
