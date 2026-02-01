from fastapi import Depends, FastAPI, Header, HTTPException, status

from . import service
from .db import init_db
from .schemas import (
    AccountCreate,
    AccountResponse,
    PaymentResponse,
    TransferRequest,
    UserCreate,
    UserResponse,
)

app = FastAPI(title="P2P Payment Service", version="0.1.0")


def init() -> None:
    init_db()


@app.on_event("startup")
def startup_event() -> None:
    init()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate) -> dict:
    try:
        return service.create_user(payload.name, payload.email)
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise HTTPException(status_code=409, detail="email_already_exists") from exc
        raise


@app.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate) -> dict:
    try:
        return service.create_account(payload.user_id, payload.currency, payload.initial_balance)
    except ValueError as exc:
        if str(exc) == "user_not_found":
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise


@app.get("/accounts/{account_id}", response_model=AccountResponse)
def get_account(account_id: str) -> dict:
    try:
        return service.get_account(account_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/payments/transfer", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def transfer(
    payload: TransferRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> dict:
    try:
        return service.transfer_funds(
            payload.sender_account_id,
            payload.receiver_account_id,
            payload.amount,
            payload.currency,
            idempotency_key,
        )
    except ValueError as exc:
        mapping = {
            "same_account_transfer": (400, "same_account_transfer"),
            "account_not_found": (404, "account_not_found"),
            "account_inactive": (409, "account_inactive"),
            "currency_mismatch": (409, "currency_mismatch"),
            "insufficient_funds": (409, "insufficient_funds"),
        }
        if str(exc) in mapping:
            status_code, detail = mapping[str(exc)]
            raise HTTPException(status_code=status_code, detail=detail) from exc
        raise


@app.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: str) -> dict:
    try:
        return service.get_payment(payment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/accounts/{account_id}/ledger")
def get_ledger(account_id: str) -> dict:
    try:
        entries = service.list_ledger(account_id)
        return {"entries": entries}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
