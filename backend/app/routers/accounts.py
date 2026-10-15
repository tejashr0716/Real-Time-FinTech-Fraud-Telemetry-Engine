from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.account import AccountResponse, MerchantResponse
from app.services.database_service import db_service

router = APIRouter(prefix="/api", tags=["Accounts & Merchants"])

@router.get("/accounts", response_model=List[AccountResponse])
async def list_accounts():
    rows = await db_service.fetch("SELECT * FROM accounts ORDER BY balance DESC")
    return [
        AccountResponse(
            id=str(r["id"]),
            account_number=r["account_number"],
            owner_name=r["owner_name"],
            email=r["email"],
            balance=float(r["balance"]),
            currency=r["currency"],
            avg_daily_spend=float(r["avg_daily_spend"]),
            risk_score=float(r["risk_score"]),
            status=r["status"],
            created_at=r["created_at"]
        )
        for r in rows
    ]

@router.get("/merchants", response_model=List[MerchantResponse])
async def list_merchants():
    rows = await db_service.fetch("SELECT * FROM merchants ORDER BY default_risk_weight DESC")
    return [
        MerchantResponse(
            id=r["id"],
            name=r["name"],
            category=r["category"],
            mcc_code=r["mcc_code"],
            default_risk_weight=float(r["default_risk_weight"]),
            country=r["country"]
        )
        for r in rows
    ]
