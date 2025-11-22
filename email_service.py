"""
Email Service - Resend Integration (User-Preferred Format)
===========================================================

Sends emails using Resend API.
Format: Numbered steps with hyperlinks (no big buttons)

Updated: November 22, 2025 - User-preferred format
"""

import os
import requests
from typing import Optional

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_API_URL = "https://api.resend.com/emails"
FROM_EMAIL = os.getenv("FROM_EMAIL", "$NIKEPIG's Massive Rocket <onboarding@resend.dev>")
BASE_URL = os.getenv("BASE_URL", "https://nike-rocket-api-production.up.railway.app")


def send_welcome_email(to_email: str, api_key: str) -> bool:
    """
    Send welcome email with API key and setup instructions
    
    Format:
    1. Your API Key
    2. Setup Agent
    3. View Dashboard
    4. Access anytime at /login
    
    Args:
        to_email: User's email address
        api_key: User's unique API key
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not RESEND_API_KEY:
        print("⚠️ RESEND_API_KEY not set - email not sent")
        print(f"🔗 Setup link (for testing): {BASE_URL}/setup?key={api_key}")
        return False
    
    setup_link = f"{BASE_URL}/setup?key={api_key}"
    dashboard_link = f"{BASE_URL}/dashboard?key={api_key}"
    login_link = f"{BASE_URL}/login"
    
    # Email HTML - User's Preferred Format
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your $NIKEPIG's Massive Rocket API Key</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background: #f5f5f5; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                            <h1 style="margin: 0; color: white; font-size: 32px; font-weight: bold;">
                                🚀 $NIKEPIG's Massive Rocket
                            </h1>
                            <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 16px;">
                                Your API Key
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Body -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            
                            <!-- Step 1: Your API Key -->
                            <h2 style="margin: 0 0 20px 0; color: #667eea; font-size: 20px;">
                                Your API Key
                            </h2>
                            <p style="margin: 0 0 15px 0; color: #374151; font-size: 14px;">
                                As requested, here's your $NIKEPIG's Massive Rocket API key:
                            </p>
                            
                            <div style="background: #f9fafb; border: 2px dashed #d1d5db; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
                                <code style="font-family: 'Courier New', monospace; font-size: 14px; color: #667eea; word-break: break-all; display: block; text-align: center;">
                                    {api_key}
                                </code>
                            </div>
                            
                            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 6px; margin-bottom: 35px;">
                                <p style="margin: 0; color: #92400e; font-size: 13px;">
                                    🔒 <strong>Security Reminder:</strong> Never share your API key with anyone. If you believe your key has been compromised, contact support immediately.
                                </p>
                            </div>
                            
                            <!-- Numbered Steps -->
                            <div style="margin-bottom: 30px;">
                                
                                <!-- Step 1: Setup Agent -->
                                <div style="padding: 18px 0; border-bottom: 1px solid #e5e7eb;">
                                    <p style="margin: 0 0 8px 0; color: #374151; font-size: 15px; font-weight: 600;">
                                        <strong style="color: #667eea;">1.</strong> Setup Your Trading Agent
                                    </p>
                                    <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px; line-height: 1.6;">
                                        Configure your automated trading agent with your Kraken API credentials. Takes 2 minutes, no technical skills required.
                                    </p>
                                    <p style="margin: 0;">
                                        <a href="{setup_link}" style="color: #667eea; text-decoration: none; font-weight: 600; font-size: 14px;">
                                            → Click here to setup agent
                                        </a>
                                    </p>
                                </div>
                                
                                <!-- Step 2: View Dashboard -->
                                <div style="padding: 18px 0; border-bottom: 1px solid #e5e7eb;">
                                    <p style="margin: 0 0 8px 0; color: #374151; font-size: 15px; font-weight: 600;">
                                        <strong style="color: #667eea;">2.</strong> View Your Dashboard
                                    </p>
                                    <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px; line-height: 1.6;">
                                        Track your trading performance in real-time. View profits, trades, and agent status.
                                    </p>
                                    <p style="margin: 0 0 5px 0;">
                                        <a href="{dashboard_link}" style="color: #667eea; text-decoration: none; font-weight: 600; font-size: 14px;">
                                            → Click here to view dashboard
                                        </a>
                                    </p>
                                    <p style="margin: 0; color: #9ca3af; font-size: 12px; font-style: italic;">
                                        💡 Tip: Bookmark this link for easy access!
                                    </p>
                                </div>
                                
                                <!-- Step 3: Access Anytime -->
                                <div style="padding: 18px 0;">
                                    <p style="margin: 0 0 8px 0; color: #374151; font-size: 15px; font-weight: 600;">
                                        <strong style="color: #667eea;">3.</strong> Access Anytime at:
                                    </p>
                                    <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px; line-height: 1.6;">
                                        Lost this email? You can always access your dashboard by entering your API key at:
                                    </p>
                                    <p style="margin: 0;">
                                        <a href="{login_link}" style="color: #667eea; text-decoration: none; font-weight: 600; font-size: 14px;">
                                            {login_link}
                                        </a>
                                    </p>
                                </div>
                                
                            </div>
                            
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 30px; background: #f9fafb; text-align: center; border-top: 1px solid #e5e7eb;">
                            <p style="margin: 0 0 10px 0; color: #6b7280; font-size: 13px;">
                                Questions? Need help? Contact us anytime.
                            </p>
                            <p style="margin: 0 0 5px 0; color: #9ca3af; font-size: 12px;">
                                $NIKEPIG's Massive Rocket - Automated Kraken Futures Trading
                            </p>
                            <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                                You're receiving this email because you signed up at {BASE_URL}
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
    
    # Plain text version
    text_content = f"""
🚀 Your $NIKEPIG's Massive Rocket API Key

Your API Key:
{api_key}

🔒 Security Reminder: Never share your API key with anyone.

Next Steps:

1. Setup Your Trading Agent
   Configure your automated trading agent with your Kraken credentials.
   → {setup_link}

2. View Your Dashboard
   Track your trading performance in real-time.
   → {dashboard_link}
   💡 Tip: Bookmark this link!

3. Access Anytime at:
   {login_link}
   Enter your API key to access your dashboard from any device.

Questions? Need help? Contact us anytime.

---
$NIKEPIG's Massive Rocket - Automated Kraken Futures Trading
You're receiving this email because you signed up at {BASE_URL}
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
                "subject": "🚀 Your $NIKEPIG's Massive Rocket API Key",
                "html": html_content,
                "text": text_content
            }
        )
        
        if response.status_code == 200:
            print(f"✅ Welcome email sent to {to_email}")
            return True
        else:
            print(f"❌ Failed to send email: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False


def send_api_key_resend_email(to_email: str, api_key: str) -> bool:
    """
    Resend API key to existing user (for "forgot key" scenarios)
    
    Args:
        to_email: User's email address
        api_key: User's existing API key
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not RESEND_API_KEY:
        print("⚠️ RESEND_API_KEY not set - email not sent")
        return False
    
    setup_link = f"{BASE_URL}/setup?key={api_key}"
    dashboard_link = f"{BASE_URL}/dashboard?key={api_key}"
    login_link = f"{BASE_URL}/login"
    
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
                    
                    <tr>
                        <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                            <h1 style="margin: 0; color: white; font-size: 32px;">🚀 $NIKEPIG's Massive Rocket</h1>
                            <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9);">Your API Key</p>
                        </td>
                    </tr>
                    
                    <tr>
                        <td style="padding: 40px 30px;">
                            <h2 style="color: #667eea; margin: 0 0 15px 0;">Your API Key</h2>
                            <p style="color: #374151; font-size: 14px; margin: 0 0 20px 0;">
                                As requested, here's your $NIKEPIG's Massive Rocket API key:
                            </p>
                            
                            <div style="background: #f9fafb; border: 2px dashed #d1d5db; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
                                <code style="font-family: 'Courier New', monospace; font-size: 14px; color: #667eea; word-break: break-all; display: block; text-align: center;">
                                    {api_key}
                                </code>
                            </div>
                            
                            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 6px; margin-bottom: 30px;">
                                <p style="margin: 0; color: #92400e; font-size: 13px;">
                                    🔒 <strong>Security Reminder:</strong> Never share your API key with anyone.
                                </p>
                            </div>
                            
                            <div style="margin-bottom: 20px;">
                                <p style="margin: 0 0 10px 0; color: #374151; font-size: 14px; font-weight: 600;">
                                    Quick Links:
                                </p>
                                <p style="margin: 0 0 8px 0;">
                                    <a href="{dashboard_link}" style="color: #667eea; text-decoration: none; font-weight: 600; font-size: 14px;">
                                        → View Dashboard
                                    </a>
                                </p>
                                <p style="margin: 0 0 8px 0;">
                                    <a href="{setup_link}" style="color: #667eea; text-decoration: none; font-weight: 600; font-size: 14px;">
                                        → Setup Agent
                                    </a>
                                </p>
                                <p style="margin: 0;">
                                    <a href="{login_link}" style="color: #667eea; text-decoration: none; font-weight: 600; font-size: 14px;">
                                        → Access Anytime: {login_link}
                                    </a>
                                </p>
                            </div>
                        </td>
                    </tr>
                    
                    <tr>
                        <td style="padding: 20px 30px; background: #f9fafb; text-align: center; border-top: 1px solid #e5e7eb;">
                            <p style="margin: 0; color: #6b7280; font-size: 12px;">
                                If you didn't request this email, please ignore it or contact support.
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
Your Nike Rocket API Key

As requested, here's your API key:

{api_key}

🔒 Security Reminder: Never share your API key with anyone.

Quick Links:
→ View Dashboard: {dashboard_link}
→ Setup Agent: {setup_link}
→ Access Anytime: {login_link}

If you didn't request this email, please ignore it or contact support.
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
                "subject": "Your $NIKEPIG's Massive Rocket API Key",
                "html": html_content,
                "text": text_content
            }
        )
        
        if response.status_code == 200:
            print(f"✅ API key resend email sent to {to_email}")
            return True
        else:
            print(f"❌ Failed to send email: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False


# Keep old functions for backward compatibility but mark as deprecated
def send_verification_email(to_email: str, verification_token: str) -> bool:
    """DEPRECATED: Use send_welcome_email() instead"""
    print("⚠️ send_verification_email() is deprecated - use send_welcome_email() instead")
    return False


def send_api_key_email(to_email: str, api_key: str) -> bool:
    """DEPRECATED: Use send_welcome_email() instead"""
    print("⚠️ send_api_key_email() is deprecated - use send_welcome_email() instead")
    return send_welcome_email(to_email, api_key)


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """DEPRECATED: Not needed for current flow"""
    print("⚠️ send_password_reset_email() is deprecated")
    return False
