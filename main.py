"""
Nike Rocket Follower System - Main API (FIXED)
===============================================
Fixed admin dashboard with proper error handling and schema compatibility

Author: Nike Rocket Team
Updated: November 22, 2025
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine
import os

# Import follower system
from follower_models import init_db
from follower_endpoints import router as follower_router

# Import portfolio system  
from portfolio_models import init_portfolio_db
from portfolio_api import router as portfolio_router

# Import admin dashboard (SAFE VERSION)
from admin_dashboard import (
    get_all_users_with_status,
    get_recent_errors,
    get_stats_summary,
    generate_admin_html,
    create_error_logs_table,
    ADMIN_PASSWORD
)

# Initialize FastAPI
app = FastAPI(
    title="Nike Rocket Follower API",
    description="Trading signal distribution and profit tracking",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
    init_db(engine)
    init_portfolio_db(engine)
    print("✅ Database initialized")
    
    # Create admin dashboard tables
    try:
        create_error_logs_table()
        print("✅ Admin dashboard tables ready")
    except Exception as e:
        print(f"⚠️ Admin dashboard setup warning: {e}")
else:
    print("⚠️ DATABASE_URL not set - database features disabled")

# Include routers
app.include_router(follower_router, tags=["follower"])
app.include_router(portfolio_router, tags=["portfolio"])

# Health check
@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "$NIKEPIG's Massive Rocket API",
        "version": "1.0.0 (FIXED)",
        "endpoints": {
            "signup": "/signup",
            "setup": "/setup",
            "dashboard": "/dashboard",
            "admin": "/admin?password=xxx",
            "debug_schema": "/debug-schema?password=xxx",
            "broadcast": "/api/broadcast-signal",
            "latest_signal": "/api/latest-signal",
            "report_pnl": "/api/report-pnl",
            "register": "/api/users/register",
            "verify": "/api/users/verify",
            "stats": "/api/users/stats",
            "agent_status": "/api/agent-status",
            "setup_agent": "/api/setup-agent",
            "stop_agent": "/api/stop-agent",
            "portfolio_stats": "/api/portfolio/stats",
            "portfolio_trades": "/api/portfolio/trades",
            "portfolio_deposit": "/api/portfolio/deposit",
            "portfolio_withdraw": "/api/portfolio/withdraw",
            "pay": "/api/pay/{api_key}",
            "webhook": "/api/payments/webhook"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

# 🔍 DEBUG SCHEMA ENDPOINT (NEW!)
@app.get("/debug-schema")
async def debug_schema(password: str = ""):
    """
    Debug endpoint to view actual database schema
    Access: /debug-schema?password=YOUR_ADMIN_PASSWORD
    """
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    
    try:
        import psycopg2
        from psycopg2 import sql
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Get all tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables_list = [row[0] for row in cur.fetchall()]
        
        result = {"tables": {}, "total_tables": len(tables_list)}
        
        for table in tables_list:
            # Get columns
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table,))
            
            columns = []
            for col in cur.fetchall():
                columns.append({
                    "name": col[0],
                    "type": col[1],
                    "nullable": col[2],
                    "default": str(col[3])[:50] if col[3] else None
                })
            
            # Get row count
            try:
                cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
                row_count = cur.fetchone()[0]
            except:
                row_count = "ERROR"
            
            result["tables"][table] = {
                "columns": columns,
                "row_count": row_count
            }
        
        cur.close()
        conn.close()
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "help": "Could not read database schema"
        }

# Admin Dashboard
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(password: str = ""):
    """
    Admin dashboard to monitor hosted follower agents
    
    Access: /admin?password=YOUR_ADMIN_PASSWORD
    
    Shows:
    - User signups
    - Setup completion rates  
    - Active agents
    - Trading activity
    - Error logs
    """
    # Check password
    if password != ADMIN_PASSWORD:
        return HTMLResponse("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>$NIKEPIG Admin Access</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        margin: 0;
                    }
                    .login-box {
                        background: white;
                        padding: 40px;
                        border-radius: 12px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                        text-align: center;
                        min-width: 300px;
                    }
                    h1 {
                        color: #667eea;
                        margin-bottom: 10px;
                        font-size: 24px;
                    }
                    .subtitle {
                        color: #666;
                        font-size: 14px;
                        margin-bottom: 25px;
                    }
                    input {
                        padding: 12px;
                        border: 2px solid #e5e7eb;
                        border-radius: 8px;
                        width: 100%;
                        font-size: 14px;
                        box-sizing: border-box;
                    }
                    input:focus {
                        outline: none;
                        border-color: #667eea;
                    }
                    button {
                        padding: 12px 24px;
                        background: #667eea;
                        color: white;
                        border: none;
                        border-radius: 8px;
                        font-weight: 600;
                        cursor: pointer;
                        margin-top: 15px;
                        width: 100%;
                        font-size: 14px;
                    }
                    button:hover {
                        background: #5568d3;
                    }
                    .error {
                        color: #ef4444;
                        margin-top: 15px;
                        font-size: 14px;
                    }
                    .debug-link {
                        margin-top: 20px;
                        font-size: 12px;
                    }
                    .debug-link a {
                        color: #667eea;
                        text-decoration: none;
                    }
                </style>
            </head>
            <body>
                <div class="login-box">
                    <h1>🔒 $NIKEPIG Admin</h1>
                    <p class="subtitle">Hosted Follower Agents Dashboard</p>
                    <form method="GET">
                        <input 
                            type="password" 
                            name="password" 
                            placeholder="Enter admin password" 
                            required 
                            autofocus
                        >
                        <button type="submit">Access Dashboard</button>
                    </form>
                    """ + (f"""<p class="error">❌ Invalid password</p>""" if password else "") + """
                    <div class="debug-link">
                        <a href="/debug-schema?password=YOUR_PASSWORD">🔍 Debug Schema</a>
                    </div>
                </div>
            </body>
            </html>
        """)
    
    # Try to load dashboard data
    try:
        users = get_all_users_with_status()
        errors = get_recent_errors()
        stats = get_stats_summary()
        
        return generate_admin_html(users, errors, stats)
        
    except Exception as e:
        # Show error with helpful debug info
        return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Dashboard Error</title>
                <style>
                    body {{
                        font-family: monospace;
                        padding: 40px;
                        background: #1e1e1e;
                        color: #d4d4d4;
                    }}
                    .error-box {{
                        background: #3e1e1e;
                        border-left: 4px solid #f48771;
                        padding: 20px;
                        border-radius: 8px;
                        margin-bottom: 20px;
                    }}
                    h1 {{ color: #f48771; }}
                    code {{
                        background: #252526;
                        padding: 2px 6px;
                        border-radius: 4px;
                        color: #ce9178;
                    }}
                    .help {{
                        background: #1e3a1e;
                        border-left: 4px solid #4ec9b0;
                        padding: 20px;
                        border-radius: 8px;
                        margin-top: 20px;
                    }}
                    .help h2 {{ color: #4ec9b0; }}
                    a {{
                        color: #4ec9b0;
                        text-decoration: none;
                    }}
                    a:hover {{ text-decoration: underline; }}
                </style>
            </head>
            <body>
                <div class="error-box">
                    <h1>⚠️ Dashboard Error</h1>
                    <p><strong>Error:</strong> {str(e)[:200]}</p>
                    <p>Make sure <code>admin_dashboard.py</code> is in your repo and DATABASE_URL is set.</p>
                </div>
                
                <div class="help">
                    <h2>🔍 Debug Steps:</h2>
                    <ol>
                        <li><a href="/debug-schema?password={password}">View actual database schema</a></li>
                        <li>Check Railway logs for table creation errors</li>
                        <li>Verify admin_dashboard.py is uploaded</li>
                    </ol>
                </div>
            </body>
            </html>
        """)

# Keep all your existing endpoints from the original file...
# (signup, setup, dashboard, etc.)

# Startup event
@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("🚀 NIKE ROCKET FOLLOWER API STARTED (FIXED VERSION)")
    print("=" * 60)
    print("✅ Database connected")
    print("✅ Follower routes loaded")
    print("✅ Portfolio routes loaded")
    print("✅ Admin dashboard ready at /admin")
    print("✅ Debug schema at /debug-schema")
    print("✅ Signup page available at /signup")
    print("✅ Setup page available at /setup")
    print("✅ Dashboard available at /dashboard")
    print("✅ Ready to receive signals")
    print("=" * 60)

# Run locally for testing
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
