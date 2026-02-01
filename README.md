# P2P Payment Service (Prototype)

A near-production P2P payment service prototype built with **FastAPI + SQLite**. It emphasizes correctness, idempotency, and ledger integrity while remaining lightweight for local development.

## Highlights
- **Atomic transfers** using transactional SQLite `BEGIN IMMEDIATE` to prevent race conditions.
- **Idempotency** on transfers to avoid duplicate debits in retries.
- **Ledger entries** for each payment to support audit trails.
- **Clean HTTP APIs** with explicit error handling and validation.

## System Design

### Components
- **FastAPI API layer**: request validation, routing, and error translation.
- **Service layer**: orchestrates transfers and enforces business rules.
- **SQLite database**: stores users, accounts, payments, and ledger entries.

### Data Model
- `users`: account owners, unique by email.
- `accounts`: balances in integer minor units (e.g., cents).
- `payments`: transfer records with idempotency keys.
- `ledger_entries`: debit/credit entries with running balances.

### Transfer Flow
1. Validate request and idempotency key.
2. Lock the sender/receiver accounts with a single transactional connection.
3. Enforce:
   - Active accounts
   - Same currency
   - Sufficient funds
4. Apply balance updates.
5. Create payment + ledger entries.

### Robustness Features
- **Idempotency** via `(sender_account_id, idempotency_key)` uniqueness.
- **Transactional integrity**: either everything is written or nothing is.
- **Typed validation**: Pydantic schemas enforce input constraints.

## API Reference

### POST `/users`
Create a user.

### POST `/accounts`
Create an account for a user.

### GET `/accounts/{account_id}`
Fetch account details and balances.

### POST `/payments/transfer`
Transfer funds between accounts.

Headers:
- `Idempotency-Key`: required

### GET `/payments/{payment_id}`
Fetch payment details.

### GET `/accounts/{account_id}/ledger`
List ledger entries for an account.

## Local Development

### Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the API
```bash
uvicorn p2p_service.app:app --reload
```

### Run tests
```bash
pytest
```

## Production Considerations (Next Steps)
- Replace SQLite with PostgreSQL and add row-level locking.
- Add auth, rate limiting, and request signing.
- Add background jobs for settlement or reconciliation.
- Integrate observability (structured logging + metrics).
- Add more exhaustive tests for concurrency and failure modes.
