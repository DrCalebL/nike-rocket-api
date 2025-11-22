"""
Portfolio API - Updated with Transaction Tracking
=================================================

New endpoints for automatic deposit/withdrawal detection.

Author: Nike Rocket Team
Updated: November 22, 2025
"""

from fastapi import APIRouter, Request, HTTPException
from balance_checker import BalanceChecker
import asyncpg
import os

router = APIRouter()

# Database connection (use your existing db_pool)
DATABASE_URL = os.getenv("DATABASE_URL")

# Create global balance checker instance
balance_checker = None

async def get_balance_checker():
    """Get or create balance checker instance"""
    global balance_checker
    if balance_checker is None:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
        balance_checker = BalanceChecker(db_pool)
    return balance_checker


@router.get("/api/portfolio/balance-summary")
async def get_balance_summary(request: Request):
    """
    Get comprehensive balance summary including deposits/withdrawals
    
    Query params:
        key: API key
    
    Returns:
        {
            "initial_capital": 10000,
            "total_deposits": 5000,
            "total_withdrawals": 2000,
            "net_deposits": 3000,
            "total_capital": 13000,
            "total_profit": 2500,
            "current_value": 15500,
            "roi_on_initial": 25.0,
            "roi_on_total": 19.23,
            "last_balance_check": "2025-11-22T10:30:00"
        }
    """
    api_key = request.headers.get("X-API-Key") or request.query_params.get("key")
    
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    try:
        checker = await get_balance_checker()
        summary = await checker.get_balance_summary(api_key)
        
        if not summary:
            return {
                "status": "not_initialized",
                "message": "Portfolio not initialized"
            }
        
        return {
            "status": "success",
            **summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio/transactions")
async def get_transactions(request: Request):
    """
    Get transaction history (deposits/withdrawals)
    
    Query params:
        key: API key
        limit: Number of transactions (default 50)
    
    Returns:
        {
            "status": "success",
            "transactions": [
                {
                    "transaction_type": "deposit",
                    "amount": 5000,
                    "balance_before": 10000,
                    "balance_after": 15000,
                    "detection_method": "automatic",
                    "created_at": "2025-11-15T10:00:00",
                    "notes": "Auto-detected deposit..."
                },
                ...
            ]
        }
    """
    api_key = request.headers.get("X-API-Key") or request.query_params.get("key")
    limit = int(request.query_params.get("limit", 50))
    
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    try:
        checker = await get_balance_checker()
        transactions = await checker.get_transaction_history(api_key, limit)
        
        return {
            "status": "success",
            "transactions": transactions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/portfolio/check-balance")
async def manual_balance_check(request: Request):
    """
    Manually trigger balance check for a user
    
    Headers:
        X-API-Key: User's API key
    
    Returns:
        {
            "status": "success",
            "message": "Balance checked",
            "detected": "deposit" or "withdrawal" or null,
            "amount": 5000 (if detected)
        }
    """
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    try:
        # Get user's Kraken credentials
        # (You'll need to adapt this to your existing code)
        checker = await get_balance_checker()
        
        # This would call check_user_balance with the user's Kraken API credentials
        # For now, just check all users
        await checker.check_all_users()
        
        return {
            "status": "success",
            "message": "Balance check initiated"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/portfolio/stats")
async def get_portfolio_stats_with_balance(request: Request):
    """
    Enhanced portfolio stats including balance information
    
    This extends your existing /api/portfolio/stats endpoint
    """
    api_key = request.headers.get("X-API-Key") or request.query_params.get("key")
    period = request.query_params.get("period", "30d")
    
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    try:
        checker = await get_balance_checker()
        
        # Get balance summary
        balance_summary = await checker.get_balance_summary(api_key)
        
        if not balance_summary:
            return {"status": "not_initialized"}
        
        # Get your existing portfolio stats
        # (You'll merge this with your existing stats calculation)
        
        return {
            "status": "success",
            "period": period,
            **balance_summary,
            # ... add your existing stats here
            "profit_factor": 2.5,  # Example
            "best_trade": 500,
            "total_trades": 45,
            # etc.
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
