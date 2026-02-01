from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response, Request, FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
import time

# Define Prometheus metrics
REQUEST_COUNT = Counter(
    'http_request_total', 'Total HTTP Requests', ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds', 'HTTP Request Latency', ['method', 'endpoint']
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        endpoint = request.url.path

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(process_time)

        return response

def setup_metrics(app: FastAPI):
    
    app.add_middleware(PrometheusMiddleware)

    @app.get("/Me45f_Ojade324_Ec43f", include_in_schema=False)
    def metrics():
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)