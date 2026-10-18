from fastapi import APIRouter

from app.api.v1 import auth, policy, beneficiaries, upload, invoices, evaluate, dashboard

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(policy.router, prefix="/policy", tags=["policy"])
api_router.include_router(beneficiaries.router, prefix="/beneficiaries", tags=["beneficiaries"])
api_router.include_router(upload.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(evaluate.router, prefix="/invoices", tags=["invoices"])
