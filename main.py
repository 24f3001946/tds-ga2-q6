from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid
import time

app = FastAPI(title="TDS GA2 Q9")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TOTAL_ORDERS = 44
RATE_LIMIT = 18
WINDOW = 10

# idempotency storage
orders_by_key = {}

# rate limit storage
client_requests = {}


class Order(BaseModel):
    item: Optional[str] = "order"
    quantity: Optional[int] = 1

@app.post("/orders", status_code=201)
def create_order(
    order: Order,
    idempotency_key: str = Header(None, alias="Idempotency-Key")
):
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Missing Idempotency-Key"
        )

    # If the same key was used before,
    # return the same order (no duplicate creation)
    if idempotency_key in orders_by_key:
        return orders_by_key[idempotency_key]

    # Create a new order
    new_order = {
        "id": str(uuid.uuid4()),
        "item": order.item,
        "quantity": order.quantity
    }

    # Store using idempotency key
    orders_by_key[idempotency_key] = new_order

    return new_order

@app.get("/orders")
def get_orders(
    limit: int = 10,
    cursor: Optional[str] = None
):
    # Convert cursor to starting position
    start = 1

    if cursor:
        start = int(cursor)

    end = min(start + limit - 1, TOTAL_ORDERS)

    items = []

    for i in range(start, end + 1):
        items.append({
            "id": i,
            "name": f"Order {i}"
        })

    # Next cursor
    if end < TOTAL_ORDERS:
        next_cursor = str(end + 1)
    else:
        next_cursor = None

    return {
        "items": items,
        "next_cursor": next_cursor
    }


@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    # Only apply rate limiting to API requests
    client_id = request.headers.get(
        "X-Client-Id",
        "anonymous"
    )

    now = time.time()

    if client_id not in client_requests:
        client_requests[client_id] = []

    # Remove expired requests
    client_requests[client_id] = [
        t for t in client_requests[client_id]
        if now - t < WINDOW
    ]

    # Check limit
    if len(client_requests[client_id]) >= RATE_LIMIT:
        return Response(
            content='{"detail":"Rate limit exceeded"}',
            status_code=429,
            headers={
                "Retry-After": "10",
                "Content-Type": "application/json"
            }
        )

    client_requests[client_id].append(now)

    response = await call_next(request)
    return response


@app.get("/")
def root():
    return {
        "message": "TDS GA2 Q9 Running"
    }
