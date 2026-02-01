from fastapi.testclient import TestClient

from p2p_service.app import app
from p2p_service.db import init_db


client = TestClient(app)


def setup_module() -> None:
    init_db()


def test_full_transfer_flow() -> None:
    user_a = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})
    user_b = client.post("/users", json={"name": "Bob", "email": "bob@example.com"})
    assert user_a.status_code == 201
    assert user_b.status_code == 201

    account_a = client.post(
        "/accounts",
        json={"user_id": user_a.json()["id"], "currency": "USD", "initial_balance": 10000},
    )
    account_b = client.post(
        "/accounts",
        json={"user_id": user_b.json()["id"], "currency": "USD", "initial_balance": 2500},
    )
    assert account_a.status_code == 201
    assert account_b.status_code == 201

    transfer = client.post(
        "/payments/transfer",
        headers={"Idempotency-Key": "transfer-1"},
        json={
            "sender_account_id": account_a.json()["id"],
            "receiver_account_id": account_b.json()["id"],
            "amount": 1500,
            "currency": "USD",
        },
    )
    assert transfer.status_code == 201
    payment = transfer.json()
    assert payment["status"] == "completed"

    duplicate = client.post(
        "/payments/transfer",
        headers={"Idempotency-Key": "transfer-1"},
        json={
            "sender_account_id": account_a.json()["id"],
            "receiver_account_id": account_b.json()["id"],
            "amount": 1500,
            "currency": "USD",
        },
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == payment["id"]

    account_a_refresh = client.get(f"/accounts/{account_a.json()['id']}")
    account_b_refresh = client.get(f"/accounts/{account_b.json()['id']}")
    assert account_a_refresh.json()["balance"] == 8500
    assert account_b_refresh.json()["balance"] == 4000
