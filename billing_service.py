"""
Nike Rocket Billing Service
===========================
Handles:
1. Monthly billing scheduler (runs 1st of month)
2. Invoice emails with payment links
3. Payment reminders (7 days, 14 days)
4. Auto-suspend after grace period (30 days)
5. Monthly counter reset

Fee Tiers:
- team: 0% (free)
- vip: 5% of profits
- standard: 10% of profits
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import asyncpg
import requests

# Configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_API_URL = "https://api.resend.com/emails"
FROM_EMAIL = os.getenv("FROM_EMAIL", "$NIKEPIG's Massive Rocket <onboarding@resend.dev>")
BASE_URL = os.getenv("BASE_URL", "https://nike-rocket-api-production.up.railway.app")
COINBASE_API_KEY = os.getenv("COINBASE_COMMERCE_API_KEY", "")

# Grace period before auto-suspend
GRACE_PERIOD_DAYS = 30
REMINDER_DAYS = [7, 14, 21]  # Send reminders at these intervals

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BILLING")


class BillingService:
    """Handles all billing operations"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.logger = logging.getLogger("BILLING")
    
    # =========================================================================
    # EMAIL FUNCTIONS
    # =========================================================================
    
    def send_invoice_email(
        self, 
        to_email: str, 
        api_key: str,
        amount: float,
        profit: float,
        fee_tier: str,
        for_month: str
    ) -> bool:
        """
        Send monthly invoice email with payment link
        """
        if not RESEND_API_KEY:
            self.logger.warning("⚠️ RESEND_API_KEY not set - email not sent")
            return False
        
        payment_link = f"{BASE_URL}/api/pay/{api_key}"
        dashboard_link = f"{BASE_URL}/dashboard?key={api_key}"
        
        fee_rates = {'team': '0%', 'vip': '5%', 'standard': '10%'}
        fee_rate_str = fee_rates.get(fee_tier, '10%')
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background: #f5f5f5; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 40px 30px; text-align: center;">
                            <h1 style="margin: 0; color: white; font-size: 28px; font-weight: bold;">
                                💰 Monthly Invoice
                            </h1>
                            <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 16px;">
                                {for_month}
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Body -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            
                            <!-- Profit Summary -->
                            <div style="background: #f0fdf4; border-radius: 12px; padding: 25px; margin-bottom: 25px; text-align: center;">
                                <p style="margin: 0 0 5px 0; color: #6b7280; font-size: 14px;">Your Profit This Month</p>
                                <p style="margin: 0; color: #059669; font-size: 36px; font-weight: bold;">
                                    ${profit:,.2f}
                                </p>
                            </div>
                            
                            <!-- Fee Breakdown -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 30px;">
                                <tr>
                                    <td style="padding: 15px 0; border-bottom: 1px solid #e5e7eb;">
                                        <span style="color: #6b7280;">Profit Share Rate ({fee_tier.upper()} tier)</span>
                                    </td>
                                    <td style="padding: 15px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">
                                        <span style="color: #374151; font-weight: 600;">{fee_rate_str}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 15px 0;">
                                        <span style="color: #374151; font-weight: 700; font-size: 18px;">Amount Due</span>
                                    </td>
                                    <td style="padding: 15px 0; text-align: right;">
                                        <span style="color: #059669; font-weight: 700; font-size: 24px;">${amount:,.2f}</span>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Payment Button -->
                            <div style="text-align: center; margin-bottom: 30px;">
                                <a href="{payment_link}" style="display: inline-block; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; text-decoration: none; padding: 16px 40px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                    💳 Pay Now with Crypto
                                </a>
                            </div>
                            
                            <p style="margin: 0; color: #9ca3af; font-size: 13px; text-align: center;">
                                Payment accepted via USDC, USDT, BTC, or ETH
                            </p>
                            
                            <!-- Grace Period Notice -->
                            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 6px; margin-top: 25px;">
                                <p style="margin: 0; color: #92400e; font-size: 13px;">
                                    ⏰ <strong>Payment Due:</strong> Please pay within 30 days to avoid trading suspension.
                                </p>
                            </div>
                            
                            <!-- Dashboard Link -->
                            <div style="margin-top: 25px; text-align: center;">
                                <a href="{dashboard_link}" style="color: #667eea; text-decoration: none; font-size: 14px;">
                                    📊 View Your Dashboard →
                                </a>
                            </div>
                            
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 25px 30px; background: #f9fafb; text-align: center; border-top: 1px solid #e5e7eb;">
                            <p style="margin: 0; color: #6b7280; font-size: 12px;">
                                🚀 $NIKEPIG's Massive Rocket | Questions? Reply to this email.
                            </p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        text_content = f"""
💰 Monthly Invoice - {for_month}

Your Profit This Month: ${profit:,.2f}
Profit Share Rate ({fee_tier.upper()} tier): {fee_rate_str}
Amount Due: ${amount:,.2f}

Pay Now: {payment_link}

Payment accepted via USDC, USDT, BTC, or ETH

⏰ Payment Due: Please pay within 30 days to avoid trading suspension.

📊 View Dashboard: {dashboard_link}

🚀 $NIKEPIG's Massive Rocket
        """
        
        try:
            response = requests.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": FROM_EMAIL,
                    "to": [to_email],
                    "subject": f"💰 Invoice: ${amount:.2f} Due - {for_month}",
                    "html": html_content,
                    "text": text_content
                }
            )
            
            if response.status_code == 200:
                self.logger.info(f"✅ Invoice email sent to {to_email}")
                return True
            else:
                self.logger.error(f"❌ Invoice email failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Invoice email error: {e}")
            return False
    
    def send_payment_reminder_email(
        self,
        to_email: str,
        api_key: str,
        amount: float,
        days_overdue: int,
        for_month: str
    ) -> bool:
        """
        Send payment reminder email
        """
        if not RESEND_API_KEY:
            return False
        
        payment_link = f"{BASE_URL}/api/pay/{api_key}"
        days_remaining = GRACE_PERIOD_DAYS - days_overdue
        
        # Urgency level
        if days_remaining <= 7:
            urgency_color = "#dc2626"  # Red
            urgency_text = "URGENT"
            urgency_emoji = "🚨"
        elif days_remaining <= 14:
            urgency_color = "#f59e0b"  # Orange
            urgency_text = "Reminder"
            urgency_emoji = "⚠️"
        else:
            urgency_color = "#3b82f6"  # Blue
            urgency_text = "Friendly Reminder"
            urgency_emoji = "💡"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background: #f5f5f5; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                    
                    <tr>
                        <td style="background: {urgency_color}; padding: 30px; text-align: center;">
                            <h1 style="margin: 0; color: white; font-size: 24px;">
                                {urgency_emoji} {urgency_text}: Payment Due
                            </h1>
                        </td>
                    </tr>
                    
                    <tr>
                        <td style="padding: 40px 30px;">
                            
                            <p style="margin: 0 0 20px 0; color: #374151; font-size: 16px;">
                                Your invoice for <strong>{for_month}</strong> is still unpaid.
                            </p>
                            
                            <div style="background: #f9fafb; border-radius: 8px; padding: 20px; margin-bottom: 25px; text-align: center;">
                                <p style="margin: 0 0 5px 0; color: #6b7280; font-size: 14px;">Amount Due</p>
                                <p style="margin: 0; color: {urgency_color}; font-size: 32px; font-weight: bold;">
                                    ${amount:,.2f}
                                </p>
                            </div>
                            
                            <div style="background: #fef2f2; border-left: 4px solid {urgency_color}; padding: 15px; border-radius: 6px; margin-bottom: 25px;">
                                <p style="margin: 0; color: #991b1b; font-size: 14px;">
                                    <strong>{days_remaining} days remaining</strong> before your trading access is suspended.
                                </p>
                            </div>
                            
                            <div style="text-align: center;">
                                <a href="{payment_link}" style="display: inline-block; background: {urgency_color}; color: white; text-decoration: none; padding: 16px 40px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                    💳 Pay Now
                                </a>
                            </div>
                            
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        try:
            response = requests.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": FROM_EMAIL,
                    "to": [to_email],
                    "subject": f"{urgency_emoji} {urgency_text}: ${amount:.2f} Payment Due",
                    "html": html_content
                }
            )
            return response.status_code == 200
        except:
            return False
    
    def send_suspension_notice_email(
        self,
        to_email: str,
        api_key: str,
        amount: float
    ) -> bool:
        """
        Send account suspension notice
        """
        if not RESEND_API_KEY:
            return False
        
        payment_link = f"{BASE_URL}/api/pay/{api_key}"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background: #f5f5f5; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; background: white; border-radius: 12px; overflow: hidden;">
                    
                    <tr>
                        <td style="background: #dc2626; padding: 30px; text-align: center;">
                            <h1 style="margin: 0; color: white; font-size: 24px;">
                                🚫 Trading Access Suspended
                            </h1>
                        </td>
                    </tr>
                    
                    <tr>
                        <td style="padding: 40px 30px;">
                            
                            <p style="margin: 0 0 20px 0; color: #374151; font-size: 16px;">
                                Your trading access has been suspended due to non-payment.
                            </p>
                            
                            <div style="background: #fef2f2; border-radius: 8px; padding: 20px; margin-bottom: 25px; text-align: center;">
                                <p style="margin: 0 0 5px 0; color: #6b7280;">Outstanding Balance</p>
                                <p style="margin: 0; color: #dc2626; font-size: 32px; font-weight: bold;">
                                    ${amount:,.2f}
                                </p>
                            </div>
                            
                            <p style="margin: 0 0 25px 0; color: #6b7280; font-size: 14px;">
                                Your trading agent has been paused and will not execute any trades until payment is received.
                            </p>
                            
                            <div style="text-align: center;">
                                <a href="{payment_link}" style="display: inline-block; background: #10b981; color: white; text-decoration: none; padding: 16px 40px; border-radius: 8px; font-weight: 600;">
                                    💳 Pay Now to Restore Access
                                </a>
                            </div>
                            
                            <p style="margin: 25px 0 0 0; color: #9ca3af; font-size: 13px; text-align: center;">
                                Access will be restored automatically within minutes of payment confirmation.
                            </p>
                            
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
        """
        
        try:
            response = requests.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": FROM_EMAIL,
                    "to": [to_email],
                    "subject": "🚫 Trading Access Suspended - Payment Required",
                    "html": html_content
                }
            )
            return response.status_code == 200
        except:
            return False
    
    # =========================================================================
    # BILLING OPERATIONS
    # =========================================================================
    
    async def process_monthly_billing(self):
        """
        Process end-of-month billing for all users
        
        Called on the 1st of each month (or manually via admin endpoint)
        """
        self.logger.info("=" * 60)
        self.logger.info("💰 PROCESSING MONTHLY BILLING")
        self.logger.info("=" * 60)
        
        previous_month = (datetime.utcnow().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        current_month = datetime.utcnow().strftime("%Y-%m")
        
        async with self.db_pool.acquire() as conn:
            # Get all users with fees due
            users = await conn.fetch("""
                SELECT 
                    id, email, api_key, fee_tier,
                    monthly_profit, monthly_fee_due, monthly_fee_paid,
                    total_profit, total_fees_paid
                FROM follower_users
                WHERE monthly_fee_due > 0
                AND monthly_fee_paid = false
                AND fee_tier != 'team'
            """)
            
            self.logger.info(f"📊 Found {len(users)} users with fees due")
            
            invoices_sent = 0
            for user in users:
                # Send invoice email
                email_sent = self.send_invoice_email(
                    to_email=user['email'],
                    api_key=user['api_key'],
                    amount=float(user['monthly_fee_due']),
                    profit=float(user['monthly_profit']),
                    fee_tier=user['fee_tier'] or 'standard',
                    for_month=previous_month
                )
                
                if email_sent:
                    invoices_sent += 1
                    
                    # Record invoice sent timestamp
                    await conn.execute("""
                        UPDATE follower_users
                        SET last_fee_calculation = CURRENT_TIMESTAMP
                        WHERE id = $1
                    """, user['id'])
            
            self.logger.info(f"✅ Sent {invoices_sent} invoice emails")
            
            # Reset monthly counters for ALL users (including team)
            await conn.execute("""
                UPDATE follower_users
                SET 
                    monthly_profit = 0,
                    monthly_trades = 0,
                    monthly_fee_paid = CASE 
                        WHEN monthly_fee_due = 0 OR fee_tier = 'team' THEN true 
                        ELSE false 
                    END
                WHERE 1=1
            """)
            
            self.logger.info(f"🔄 Reset monthly counters for {current_month}")
            
        return {
            "status": "success",
            "invoices_sent": invoices_sent,
            "for_month": previous_month,
            "reset_for": current_month
        }
    
    async def send_payment_reminders(self):
        """
        Send reminders to users with overdue payments
        
        Called daily to check for overdue invoices
        """
        self.logger.info("📧 Checking for payment reminders...")
        
        async with self.db_pool.acquire() as conn:
            # Get users with unpaid fees and last_fee_calculation set
            users = await conn.fetch("""
                SELECT 
                    id, email, api_key, fee_tier,
                    monthly_fee_due, last_fee_calculation
                FROM follower_users
                WHERE monthly_fee_due > 0
                AND monthly_fee_paid = false
                AND last_fee_calculation IS NOT NULL
                AND access_granted = true
                AND fee_tier != 'team'
            """)
            
            reminders_sent = 0
            for user in users:
                days_overdue = (datetime.utcnow() - user['last_fee_calculation']).days
                
                # Check if we should send a reminder
                if days_overdue in REMINDER_DAYS:
                    for_month = user['last_fee_calculation'].strftime("%Y-%m")
                    
                    email_sent = self.send_payment_reminder_email(
                        to_email=user['email'],
                        api_key=user['api_key'],
                        amount=float(user['monthly_fee_due']),
                        days_overdue=days_overdue,
                        for_month=for_month
                    )
                    
                    if email_sent:
                        reminders_sent += 1
                        self.logger.info(f"📧 Reminder sent to {user['email']} ({days_overdue} days overdue)")
            
            self.logger.info(f"✅ Sent {reminders_sent} payment reminders")
            
        return {"reminders_sent": reminders_sent}
    
    async def process_auto_suspensions(self):
        """
        Suspend users who haven't paid after grace period
        
        Called daily to check for overdue accounts
        """
        self.logger.info("🔒 Checking for auto-suspensions...")
        
        async with self.db_pool.acquire() as conn:
            # Get users past grace period
            users = await conn.fetch("""
                SELECT 
                    id, email, api_key, monthly_fee_due, last_fee_calculation
                FROM follower_users
                WHERE monthly_fee_due > 0
                AND monthly_fee_paid = false
                AND last_fee_calculation IS NOT NULL
                AND access_granted = true
                AND fee_tier != 'team'
                AND last_fee_calculation < $1
            """, datetime.utcnow() - timedelta(days=GRACE_PERIOD_DAYS))
            
            suspended = 0
            for user in users:
                # Suspend user
                await conn.execute("""
                    UPDATE follower_users
                    SET 
                        access_granted = false,
                        agent_active = false,
                        suspended_at = CURRENT_TIMESTAMP,
                        suspension_reason = 'Non-payment of fees'
                    WHERE id = $1
                """, user['id'])
                
                # Send suspension notice
                self.send_suspension_notice_email(
                    to_email=user['email'],
                    api_key=user['api_key'],
                    amount=float(user['monthly_fee_due'])
                )
                
                suspended += 1
                self.logger.warning(f"🚫 Suspended {user['email']} for non-payment")
            
            self.logger.info(f"🔒 Suspended {suspended} accounts")
            
        return {"suspended": suspended}
    
    async def get_billing_summary(self) -> dict:
        """
        Get current billing summary for admin dashboard
        """
        async with self.db_pool.acquire() as conn:
            summary = await conn.fetchrow("""
                SELECT 
                    COUNT(*) FILTER (WHERE monthly_fee_due > 0 AND monthly_fee_paid = false) as unpaid_count,
                    COALESCE(SUM(monthly_fee_due) FILTER (WHERE monthly_fee_paid = false), 0) as total_unpaid,
                    COUNT(*) FILTER (WHERE monthly_fee_paid = true AND monthly_fee_due > 0) as paid_count,
                    COALESCE(SUM(total_fees_paid), 0) as total_collected,
                    COUNT(*) FILTER (WHERE fee_tier = 'team') as team_count,
                    COUNT(*) FILTER (WHERE fee_tier = 'vip') as vip_count,
                    COUNT(*) FILTER (WHERE fee_tier = 'standard') as standard_count,
                    COUNT(*) FILTER (WHERE access_granted = false AND suspension_reason = 'Non-payment of fees') as suspended_count
                FROM follower_users
            """)
            
            return {
                "unpaid_invoices": summary['unpaid_count'],
                "total_unpaid": float(summary['total_unpaid']),
                "paid_invoices": summary['paid_count'],
                "total_collected": float(summary['total_collected']),
                "users_by_tier": {
                    "team": summary['team_count'],
                    "vip": summary['vip_count'],
                    "standard": summary['standard_count']
                },
                "suspended_for_nonpayment": summary['suspended_count']
            }


# =============================================================================
# BACKGROUND SCHEDULER
# =============================================================================

async def billing_scheduler(db_pool: asyncpg.Pool):
    """
    Background scheduler for billing tasks
    
    Runs daily to:
    - Check if it's the 1st of the month (process billing)
    - Send payment reminders
    - Process auto-suspensions
    """
    logger.info("📅 Billing scheduler started")
    
    billing = BillingService(db_pool)
    last_monthly_run = None
    
    while True:
        try:
            now = datetime.utcnow()
            
            # Check if it's the 1st of the month and we haven't run yet today
            if now.day == 1 and last_monthly_run != now.date():
                logger.info("🗓️ First of month - running monthly billing...")
                await billing.process_monthly_billing()
                last_monthly_run = now.date()
            
            # Daily tasks (run at ~8am UTC)
            if now.hour == 8:
                await billing.send_payment_reminders()
                await billing.process_auto_suspensions()
            
            # Sleep for 1 hour
            await asyncio.sleep(3600)
            
        except asyncio.CancelledError:
            logger.info("📅 Billing scheduler stopped")
            break
        except Exception as e:
            logger.error(f"❌ Billing scheduler error: {e}")
            await asyncio.sleep(300)  # Wait 5 min on error


async def start_billing_scheduler(db_pool: asyncpg.Pool):
    """Entry point for billing scheduler (call from main.py)"""
    await asyncio.sleep(60)  # Wait for app startup
    logger.info("💰 Starting billing scheduler...")
    await billing_scheduler(db_pool)
