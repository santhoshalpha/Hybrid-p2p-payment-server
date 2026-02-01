from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=255)


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: str


class AccountCreate(BaseModel):
    user_id: str
    currency: str = Field(..., min_length=3, max_length=3)
    initial_balance: int = Field(ge=0)


class AccountResponse(BaseModel):
    id: str
    user_id: str
    currency: str
    balance: int
    status: str
    created_at: str


class TransferRequest(BaseModel):
    sender_account_id: str
    receiver_account_id: str
    amount: int = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)


class PaymentResponse(BaseModel):
    id: str
    sender_account_id: str
    receiver_account_id: str
    amount: int
    currency: str
    status: str
    created_at: str
