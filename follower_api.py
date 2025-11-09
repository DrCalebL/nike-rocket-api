"""
Nike Rocket Follower API - Coinbase Commerce Version
-----------------------------------------------------
Central hub for the follower system:
1. Receives trade signals from your algo
2. Manages user signups and API keys
3. Forwards signals to active follower agents
4. Tracks P&L for profit share calculation
5. Enforces payment access control
6. Processes payments via Coinbase Commerce (crypto)

Deploy this to Railway (free tier works!)
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import secrets
import os
import json
from pathlib import Path
import httpx
import hmac
import hashlib

app = FastAPI(title="Nike Rocket Follower API")

# CORS for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
ADMIN_SECRET_KEY = os.getenv('ADMIN_SECRET_KEY', 'your-admin-key-change-this')
COINBASE_COMMERCE_API_KEY = os.getenv('COINBASE_COMMERCE_API_KEY')
COINBASE_WEBHOOK_SECRET = os.getenv('COINBASE_WEBHOOK_SECRET')
DATABASE_FILE = 'users_database.json'

# ============================================================================
# DATA MODELS
# ============================================================================

class SignupRequest(BaseModel):
    email: EmailStr

class VerifyRequest(BaseModel):
    api_key: str

class TradeReport(BaseModel):
    api_key: str
    symbol: str
    side: str  # 'LONG' or 'SHORT'
    entry_price: float
    exit_price: float
    size: float
    timestamp: Optional[str] = None

class BroadcastRequest(BaseModel):
    signal: Dict
    admin_key: str

# ============================================================================
# DATABASE (Simple JSON - upgrade to PostgreSQL later if needed)
# ============================================================================

class Database:
    """Simple JSON database for MVP. Upgrade to PostgreSQL for production."""
    
    def __init__(self, filepath: str = DATABASE_FILE):
        self.filepath = filepath
        self.data = self.load()
    
    def load(self) -> Dict:
        """Load database from JSON file"""
        if Path(self.filepath).exists():
            with open(self.filepath, 'r') as f:
                return json.load(f)
        return {
            'users': {},
            'trades': [],
            'signals': []
        }
    
    def save(self):
        """Save database to JSON file"""
        with open(self.filepath, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)
    
    def get_user_by_api_key(self, api_key: str) -> Optional[Dict]:
        """Get user by their API key"""
        return self.data['users'].get(api_key)
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        for api_key, user in self.data['users'].items():
            if user['email'] == email:
                return user
        return None
    
    def create_user(self, email: str, api_key: str) -> Dict:
        """Create new user"""
        user = {
            'email': email,
            'api_key': api_key,
            'created_at': datetime.now().isoformat(),
            'access_active': True,
            'monthly_pnl': 0.0,
            'profit_share_due': 0.0,
            'profit_share_paid': False,
            'payment_due_date': None,
            'total_trades': 0,
            'coinbase_charge_id': None
        }
        self.data['users'][api_key] = user
        self.save()
        return user
    
    def update_user(self, api_key: str, updates: Dict):
        """Update user data"""
        if api_key in self.data['users']:
            self.data['users'][api_key].update(updates)
            self.save()
    
    def get_all_active_users(self) -> List[Dict]:
        """Get all users with active access"""
        return [
            user for user in self.data['users'].values()
            if user.get('access_active', False)
        ]
    
    def add_trade(self, trade: Dict):
        """Record a trade"""
        trade['recorded_at'] = datetime.now().isoformat()
        self.data['trades'].append(trade)
        self.save()
    
    def add_signal(self, signal: Dict):
        """Record a signal broadcast"""
        signal['broadcast_at'] = datetime.now().isoformat()
        self.data['signals'].append(signal)
        self.save()

# Global database instance
db = Database()

# ============================================================================
# COINBASE COMMERCE INTEGRATION
# ============================================================================

async def create_coinbase_charge(amount: float, user_api_key: str, user_email: str):
    """Create a Coinbase Commerce charge for payment"""
    
    if not COINBASE_COMMERCE_API_KEY:
        raise HTTPException(status_code=500, detail="Coinbase Commerce not configured")
    
    url = "https://api.commerce.coinbase.com/charges"
    
    headers = {
        "Content-Type": "application/json",
        "X-CC-Api-Key": COINBASE_COMMERCE_API_KEY,
        "X-CC-Version": "2018-03-22"
    }
    
    payload = {
        "name": "Nike Rocket Profit Share",
        "description": f"Monthly profit share (5% of ${amount:.2f} profits)",
        "pricing_type": "fixed_price",
        "local_price": {
            "amount": str(amount),
            "currency": "USD"
        },
        "metadata": {
            "api_key": user_api_key,
            "email": user_email,
            "type": "profit_share"
        },
        "redirect_url": f"https://nikerocket.io/payment-success?api_key={user_api_key}",
        "cancel_url": f"https://nikerocket.io/payment-cancelled"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        
        if response.status_code != 201:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Coinbase Commerce error: {response.text}"
            )
        
        return response.json()

def verify_coinbase_webhook(payload: bytes, signature: str) -> bool:
    """Verify webhook came from Coinbase Commerce"""
    if not COINBASE_WEBHOOK_SECRET:
        return True  # Skip verification if no secret set (for testing)
    
    computed_signature = hmac.new(
        COINBASE_WEBHOOK_SECRET.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed_signature, signature)

# ============================================================================
# AUTHENTICATION
# ============================================================================

def verify_admin_key(admin_key: str):
    """Verify admin key for protected endpoints"""
    if admin_key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

# ============================================================================
# API ENDPOINTS - USER MANAGEMENT
# ============================================================================

@app.get("/")
def root():
    """Health check"""
    return {
        "service": "Nike Rocket Follower API",
        "status": "operational",
        "version": "2.0.0",
        "payment_provider": "Coinbase Commerce"
    }

@app.post("/signup")
def signup(request: SignupRequest):
    """
    User signup - FREE!
    Returns API key for their agent
    """
    try:
        # Check if email already exists
        existing_user = db.get_user_by_email(request.email)
        if existing_user:
            return {
                'message': 'Email already registered',
                'api_key': existing_user['api_key']
            }
        
        # Generate unique API key
        api_key = f"NK_{secrets.token_urlsafe(32)}"
        
        # Create user
        user = db.create_user(request.email, api_key)
        
        return {
            'message': 'Signup successful!',
            'api_key': api_key,
            'email': request.email,
            'agent_deploy_url': 'https://render.com/deploy?repo=https://github.com/nikerocket/kraken-follower-agent',
            'instructions': {
                'step1': 'Click the deploy URL above',
                'step2': 'Paste your API key when prompted',
                'step3': 'Enter your Kraken Futures API key',
                'step4': 'Set your portfolio size',
                'step5': 'Click Deploy - done in 2 minutes!'
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")

@app.post("/verify")
def verify_access(request: VerifyRequest):
    """
    Verify if user has active access
    Called by follower agent on startup and before each trade
    """
    try:
        user = db.get_user_by_api_key(request.api_key)
        
        if not user:
            return {
                'active': False,
                'reason': 'invalid_key',
                'message': 'Invalid API key'
            }
        
        # Check if profit share is overdue
        if user.get('profit_share_due', 0) > 0 and not user.get('profit_share_paid', False):
            due_date = user.get('payment_due_date')
            if due_date:
                due_date = datetime.fromisoformat(due_date)
                days_overdue = (datetime.now() - due_date).days
                
                if days_overdue > 7:  # 7-day grace period
                    return {
                        'active': False,
                        'reason': 'payment_overdue',
                        'amount_due': user['profit_share_due'],
                        'days_overdue': days_overdue,
                        'payment_url': f'https://your-api-url.railway.app/pay/{user["api_key"]}',
                        'message': f"""
⚠️ Access Suspended

Outstanding profit share: ${user['profit_share_due']:.2f} (5% of profits)
Overdue by: {days_overdue} days

Pay with crypto here:
https://your-api-url.railway.app/pay/{user['api_key']}

Your agent will resume automatically after payment.
                        """
                    }
        
        return {
            'active': True,
            'email': user['email'],
            'monthly_pnl': user.get('monthly_pnl', 0)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

# ============================================================================
# API ENDPOINTS - TRADE TRACKING
# ============================================================================

@app.post("/track-trade")
def track_trade(report: TradeReport):
    """
    Record trade P&L from follower agent
    Used to calculate monthly profit share
    """
    try:
        user = db.get_user_by_api_key(report.api_key)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Calculate P&L
        if report.side == 'LONG':
            pnl = (report.exit_price - report.entry_price) * report.size
        else:  # SHORT
            pnl = (report.entry_price - report.exit_price) * report.size
        
        # Update user's monthly P&L
        user['monthly_pnl'] = user.get('monthly_pnl', 0) + pnl
        user['total_trades'] = user.get('total_trades', 0) + 1
        db.update_user(report.api_key, user)
        
        # Record trade
        trade = {
            'api_key': report.api_key,
            'email': user['email'],
            'symbol': report.symbol,
            'side': report.side,
            'entry_price': report.entry_price,
            'exit_price': report.exit_price,
            'size': report.size,
            'pnl': pnl,
            'timestamp': report.timestamp or datetime.now().isoformat()
        }
        db.add_trade(trade)
        
        return {
            'success': True,
            'pnl': pnl,
            'monthly_pnl': user['monthly_pnl'],
            'total_trades': user['total_trades']
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trade tracking failed: {str(e)}")

# ============================================================================
# API ENDPOINTS - SIGNAL BROADCASTING
# ============================================================================

@app.post("/signal/broadcast")
def broadcast_signal(request: BroadcastRequest):
    """
    Receive signal from your algo and forward to all active followers
    Only callable by you (requires admin key)
    """
    try:
        # Verify admin authentication
        verify_admin_key(request.admin_key)
        
        signal = request.signal
        
        # Record signal
        db.add_signal(signal)
        
        # Get all active users
        active_users = db.get_all_active_users()
        
        sent_count = len(active_users)
        blocked_count = len(db.data['users']) - sent_count
        
        return {
            'success': True,
            'sent': sent_count,
            'blocked': blocked_count,
            'signal': signal,
            'timestamp': datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Broadcast failed: {str(e)}")

@app.get("/signal/latest")
def get_latest_signal(api_key: str):
    """
    Get latest signal (for follower agents to poll)
    Requires valid API key with active access
    """
    try:
        # Verify user has access
        user = db.get_user_by_api_key(api_key)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        verification = verify_access(VerifyRequest(api_key=api_key))
        if not verification.get('active'):
            raise HTTPException(status_code=403, detail="Access suspended")
        
        # Get latest signal
        if db.data['signals']:
            latest_signal = db.data['signals'][-1]
            return {
                'signal': latest_signal,
                'timestamp': latest_signal.get('broadcast_at')
            }
        
        return {
            'signal': None,
            'message': 'No signals yet'
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get signal: {str(e)}")

# ============================================================================
# API ENDPOINTS - PAYMENT (Coinbase Commerce)
# ============================================================================

@app.get("/pay/{api_key}")
async def create_payment_link(api_key: str):
    """
    Generate Coinbase Commerce payment link for profit share
    """
    try:
        user = db.get_user_by_api_key(api_key)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user.get('profit_share_due', 0) <= 0:
            return {
                'message': 'No payment due',
                'amount': 0
            }
        
        # Create Coinbase Commerce charge
        charge = await create_coinbase_charge(
            amount=user['profit_share_due'],
            user_api_key=api_key,
            user_email=user['email']
        )
        
        # Save charge ID for tracking
        db.update_user(api_key, {
            'coinbase_charge_id': charge['data']['id']
        })
        
        return {
            'payment_url': charge['data']['hosted_url'],
            'amount': user['profit_share_due'],
            'charge_id': charge['data']['id'],
            'instructions': {
                '1': 'Click payment_url above',
                '2': 'Choose your crypto (USDC, USDT, BTC, ETH)',
                '3': 'Send from your wallet',
                '4': 'Access restores automatically after confirmation'
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment link creation failed: {str(e)}")

@app.post("/webhook/coinbase")
async def coinbase_webhook(request: Request):
    """
    Handle Coinbase Commerce webhook events
    Automatically restore access when payment received
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        signature = request.headers.get('X-CC-Webhook-Signature', '')
        
        # Verify webhook signature
        if not verify_coinbase_webhook(body, signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse event
        event = json.loads(body)
        event_type = event.get('event', {}).get('type')
        
        # Handle charge confirmed event
        if event_type == 'charge:confirmed':
            charge_data = event.get('event', {}).get('data', {})
            metadata = charge_data.get('metadata', {})
            api_key = metadata.get('api_key')
            
            if api_key:
                user = db.get_user_by_api_key(api_key)
                if user:
                    # Mark as paid and restore access
                    db.update_user(api_key, {
                        'profit_share_paid': True,
                        'access_active': True,
                        'profit_share_due': 0,
                        'payment_confirmed_at': datetime.now().isoformat()
                    })
                    
                    print(f"✅ Payment confirmed for {user['email']}")
                    
                    return {'status': 'success', 'message': 'Payment confirmed'}
        
        return {'status': 'ignored', 'event_type': event_type}
    
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

# ============================================================================
# API ENDPOINTS - ADMIN
# ============================================================================

@app.get("/admin/stats")
def admin_stats(admin_key: str):
    """
    Admin dashboard stats
    """
    try:
        verify_admin_key(admin_key)
        
        total_users = len(db.data['users'])
        active_users = len(db.get_all_active_users())
        total_trades = len(db.data['trades'])
        total_signals = len(db.data['signals'])
        
        # Calculate revenue
        total_profit_share_due = sum(
            user.get('profit_share_due', 0) 
            for user in db.data['users'].values()
        )
        total_profit_share_paid = sum(
            user.get('profit_share_due', 0) 
            for user in db.data['users'].values()
            if user.get('profit_share_paid', False)
        )
        
        return {
            'users': {
                'total': total_users,
                'active': active_users,
                'suspended': total_users - active_users
            },
            'trades': {
                'total': total_trades
            },
            'signals': {
                'total': total_signals
            },
            'revenue': {
                'pending': total_profit_share_due - total_profit_share_paid,
                'collected': total_profit_share_paid,
                'total': total_profit_share_due
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats failed: {str(e)}")

@app.post("/admin/calculate-fees")
def calculate_monthly_fees(admin_key: str):
    """
    Run monthly fee calculation
    Called manually or via cron job on 1st of month
    """
    try:
        verify_admin_key(admin_key)
        
        fee_count = 0
        no_fee_count = 0
        
        for api_key, user in db.data['users'].items():
            monthly_pnl = user.get('monthly_pnl', 0)
            
            if monthly_pnl > 0:
                # Calculate 5% profit share
                profit_share = monthly_pnl * 0.05
                
                db.update_user(api_key, {
                    'profit_share_due': profit_share,
                    'profit_share_paid': False,
                    'payment_due_date': (datetime.now() + timedelta(days=7)).isoformat(),
                    'monthly_pnl': 0  # Reset for next month
                })
                
                fee_count += 1
                
                # TODO: Send email invoice
            else:
                # No profit = no fee
                db.update_user(api_key, {
                    'monthly_pnl': 0  # Reset for next month
                })
                
                no_fee_count += 1
                
                # TODO: Send "no fee" email
        
        return {
            'success': True,
            'fees_created': fee_count,
            'no_fees': no_fee_count,
            'total_users': len(db.data['users'])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fee calculation failed: {str(e)}")

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Nike Rocket Follower API Starting...")
    print(f"💳 Payment Provider: Coinbase Commerce")
    print(f"📊 Database: {DATABASE_FILE}")
    print(f"👥 Users: {len(db.data['users'])}")
    print(f"📡 Signals: {len(db.data['signals'])}")
    print(f"💰 Trades: {len(db.data['trades'])}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
