import uuid
from datetime import datetime, timezone
from typing import Iterable, Mapping

from .db import transaction

ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime(ISO_FORMAT)


def _row_to_dict(row: Mapping) -> dict:
    return dict(row)


def create_user(name: str, email: str) -> dict:
    user_id = str(uuid.uuid4())
    created_at = _utc_now()
    with transaction() as conn:
        conn.execute(
            "INSERT INTO users (id, name, email, created_at) VALUES (?, ?, ?, ?)",
            (user_id, name, email, created_at),
        )
    return {
        "id": user_id,
        "name": name,
        "email": email,
        "created_at": created_at,
    }


def create_account(user_id: str, currency: str, initial_balance: int) -> dict:
    account_id = str(uuid.uuid4())
    created_at = _utc_now()
    with transaction() as conn:
        user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if user is None:
            raise ValueError("user_not_found")
        conn.execute(
            "INSERT INTO accounts (id, user_id, currency, balance, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (account_id, user_id, currency.upper(), initial_balance, "active", created_at),
        )
    return {
        "id": account_id,
        "user_id": user_id,
        "currency": currency.upper(),
        "balance": initial_balance,
        "status": "active",
        "created_at": created_at,
    }


def get_account(account_id: str) -> dict:
    with transaction() as conn:
        row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if row is None:
            raise ValueError("account_not_found")
        return _row_to_dict(row)


def get_payment(payment_id: str) -> dict:
    with transaction() as conn:
        row = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
        if row is None:
            raise ValueError("payment_not_found")
        return _row_to_dict(row)


def transfer_funds(
    sender_account_id: str,
    receiver_account_id: str,
    amount: int,
    currency: str,
    idempotency_key: str,
) -> dict:
    if sender_account_id == receiver_account_id:
        raise ValueError("same_account_transfer")

    currency = currency.upper()
    with transaction() as conn:
        existing = conn.execute(
            "SELECT * FROM payments WHERE sender_account_id = ? AND idempotency_key = ?",
            (sender_account_id, idempotency_key),
        ).fetchone()
        if existing is not None:
            return _row_to_dict(existing)

        sender = conn.execute("SELECT * FROM accounts WHERE id = ?", (sender_account_id,)).fetchone()
        receiver = conn.execute("SELECT * FROM accounts WHERE id = ?", (receiver_account_id,)).fetchone()
        if sender is None or receiver is None:
            raise ValueError("account_not_found")
        if sender["status"] != "active" or receiver["status"] != "active":
            raise ValueError("account_inactive")
        if sender["currency"] != currency or receiver["currency"] != currency:
            raise ValueError("currency_mismatch")
        if sender["balance"] < amount:
            raise ValueError("insufficient_funds")

        payment_id = str(uuid.uuid4())
        created_at = _utc_now()

        new_sender_balance = sender["balance"] - amount
        new_receiver_balance = receiver["balance"] + amount

        conn.execute(
            "UPDATE accounts SET balance = ? WHERE id = ?",
            (new_sender_balance, sender_account_id),
        )
        conn.execute(
            "UPDATE accounts SET balance = ? WHERE id = ?",
            (new_receiver_balance, receiver_account_id),
        )
        conn.execute(
            "INSERT INTO payments (id, sender_account_id, receiver_account_id, amount, currency, status, idempotency_key, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                payment_id,
                sender_account_id,
                receiver_account_id,
                amount,
                currency,
                "completed",
                idempotency_key,
                created_at,
            ),
        )

        ledger_entries = [
            (
                str(uuid.uuid4()),
                sender_account_id,
                payment_id,
                "debit",
                amount,
                new_sender_balance,
                created_at,
            ),
            (
                str(uuid.uuid4()),
                receiver_account_id,
                payment_id,
                "credit",
                amount,
                new_receiver_balance,
                created_at,
            ),
        ]
        conn.executemany(
            "INSERT INTO ledger_entries (id, account_id, payment_id, direction, amount, balance_after, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ledger_entries,
        )

        return {
            "id": payment_id,
            "sender_account_id": sender_account_id,
            "receiver_account_id": receiver_account_id,
            "amount": amount,
            "currency": currency,
            "status": "completed",
            "created_at": created_at,
        }


def list_ledger(account_id: str) -> Iterable[dict]:
    with transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM ledger_entries WHERE account_id = ? ORDER BY created_at DESC",
            (account_id,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
