from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .infrai_client import InfraiClient, InfraiError
from .payment_review import AuditNotification, ReviewRequest, review_payment

app = FastAPI(title="Payment Knowledge Review")


@app.exception_handler(InfraiError)
async def infrai_rejection(_: Request, exc: InfraiError) -> JSONResponse:
    status = exc.status_code if 400 <= exc.status_code < 500 else 502
    return JSONResponse(status_code=status, content={"error": {"code": exc.code, "message": str(exc)}})


@app.post("/review", response_model=AuditNotification)
def review(request: ReviewRequest) -> AuditNotification:
    client = InfraiClient()
    try:
        return review_payment(request, client)
    finally:
        client.close()
