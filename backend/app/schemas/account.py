from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AccountResponse(BaseModel):
    id: str
    account_number: str
    owner_name: str
    email: str
    balance: float
    currency: str
    avg_daily_spend: float
    risk_score: float
    status: str
    created_at: Optional[datetime] = None

class MerchantResponse(BaseModel):
    id: str
    name: str
    category: str
    mcc_code: str
    default_risk_weight: float
    country: str
