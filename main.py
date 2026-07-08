from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import uuid
import time
from collections import deque

EMAIL = "24f3001946@ds.study.iitm.ac.in"

app = FastAPI(title="TDS GA2 Q6")

# Allow browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup time
START_TIME = time.time()

# Prometheus counter
REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP Requests"
)

# Keep the last 100 log entries
LOGS = deque(maxlen=100)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())

    REQUEST_COUNTER.inc()

    response = await call_next(request)

    LOGS.append({
        "level": "INFO",
        "ts": time.time(),
        "path": request.url.path,
        "request_id": request_id
    })

    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/work")
def work(n: int = 1):
    return {
        "email": EMAIL,
        "done": n
    }


@app.get("/healthz")
def health():
    return {
        "status": "ok",
        "uptime_s": round(time.time() - START_TIME, 3)
    }

@app.get("/metrics")
def metrics():
    return PlainTextResponse(
        generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/logs/tail")
def tail(limit: int = 10):
    limit = max(0, min(limit, len(LOGS)))
    return list(LOGS)[-limit:]


@app.get("/")
def root():
    return {
        "message": "TDS GA2 Q6 Running"
    }
