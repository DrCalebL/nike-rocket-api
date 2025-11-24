"""
Admin Dashboard - STREAMLINED VERSION
======================================
Uses SAME tables as user dashboard (no duplicate data)
Keeps error_logs and agent_logs for troubleshooting

TABLES USED:
- follower_users     (from user dashboard - user info)
- portfolio_users    (from user dashboard - capital tracking)
- portfolio_trades   (from user dashboard - trade records)
- error_logs         (admin only - troubleshooting)
- agent_logs         (admin only - heartbeats/debugging)
"""

import os
import psycopg2
from datetime import datetime
from typing import List, Dict, Optional

DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme123")


def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def table_exists(table_name: str) -> bool:
    """Check if a table exists"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, (table_name,))
        exists = cur.fetchone()[0]
        cur.close()
        conn.close()
        return exists
    except:
        return False


def create_admin_tables():
    """
    Create ONLY admin-specific tables for troubleshooting
    (error_logs and agent_logs - not duplicated elsewhere)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Error logs - for troubleshooting without needing Kraken API keys
    cur.execute("""
        CREATE TABLE IF NOT EXISTS error_logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            api_key VARCHAR(100),
            error_type VARCHAR(100),
            error_message TEXT,
            context JSONB
        )
    """)
    
    # Agent logs - for heartbeats and remote debugging
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            api_key VARCHAR(100),
            event_type VARCHAR(100),
            event_data JSONB
        )
    """)
    
    # Indexes for fast queries
    cur.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp ON error_logs(timestamp DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_api_key ON error_logs(api_key)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_timestamp ON agent_logs(timestamp DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_api_key ON agent_logs(api_key)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_event ON agent_logs(event_type)")
    
    conn.commit()
    cur.close()
    conn.close()


# Alias for backwards compatibility with main.py
create_error_logs_table = create_admin_tables


def get_all_users_with_status() -> List[Dict]:
    """
    Get all users with their status and stats
    
    USES:
    - follower_users (user info, agent status)
    - portfolio_users (capital info)
    - portfolio_trades (trade stats via pnl_usd)
    - agent_logs (heartbeat for active status)
    - error_logs (recent errors)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    if not table_exists('follower_users'):
        cur.close()
        conn.close()
        return []
    
    try:
        cur.execute("""
            SELECT 
                fu.id,
                fu.email, 
                fu.api_key,
                fu.agent_active,
                fu.credentials_set,
                fu.created_at
            FROM follower_users fu
            ORDER BY fu.id DESC
        """)
        
        users = []
        for row in cur.fetchall():
            user_id, email, api_key, agent_active, credentials_set, created_at = row
            
            # Determine agent status
            status = {'status': 'pending', 'status_text': 'Setup Pending', 'emoji': '⏳', 'detail': 'Needs setup'}
            
            if credentials_set:
                status = {'status': 'ready', 'status_text': 'Ready', 'emoji': '🟡', 'detail': 'Configured'}
            
            if agent_active:
                status = {'status': 'active', 'status_text': 'Active', 'emoji': '🟢', 'detail': 'Running'}
            
            # Check for recent heartbeat
            if table_exists('agent_logs'):
                cur.execute("""
                    SELECT timestamp FROM agent_logs 
                    WHERE api_key = %s AND event_type = 'heartbeat'
                    ORDER BY timestamp DESC LIMIT 1
                """, (api_key,))
                heartbeat = cur.fetchone()
                
                if heartbeat:
                    time_diff = (datetime.utcnow() - heartbeat[0]).total_seconds()
                    if time_diff < 300:
                        status = {'status': 'active', 'status_text': 'Active', 'emoji': '🟢', 'detail': f'{int(time_diff)}s ago'}
                    elif time_diff < 3600:
                        status = {'status': 'idle', 'status_text': 'Idle', 'emoji': '🟠', 'detail': f'{int(time_diff/60)}m ago'}
            
            # Get portfolio stats
            initial_capital = 0.0
            current_value = 0.0
            total_profit = 0.0
            total_trades = 0
            
            if table_exists('portfolio_users'):
                cur.execute("""
                    SELECT pu.id, pu.initial_capital, pu.last_known_balance
                    FROM portfolio_users pu WHERE pu.api_key = %s
                """, (api_key,))
                portfolio = cur.fetchone()
                
                if portfolio:
                    pu_id, initial_capital, last_balance = portfolio
                    initial_capital = float(initial_capital or 0)
                    current_value = float(last_balance or initial_capital)
                    
                    if table_exists('portfolio_trades'):
                        cur.execute("""
                            SELECT COUNT(*), COALESCE(SUM(pnl_usd), 0)
                            FROM portfolio_trades WHERE user_id = %s
                        """, (pu_id,))
                        trade_stats = cur.fetchone()
                        if trade_stats:
                            total_trades = trade_stats[0] or 0
                            total_profit = float(trade_stats[1] or 0)
            
            # Get recent errors
            recent_errors = 0
            if table_exists('error_logs'):
                cur.execute("""
                    SELECT COUNT(*) FROM error_logs 
                    WHERE api_key = %s AND timestamp > NOW() - INTERVAL '24 hours'
                """, (api_key,))
                recent_errors = cur.fetchone()[0] or 0
            
            roi = (total_profit / initial_capital * 100) if initial_capital > 0 else 0
            
            users.append({
                'email': email,
                'api_key': api_key,
                'agent_status': status['status'],
                'status_text': status['status_text'],
                'status_emoji': status['emoji'],
                'status_detail': status['detail'],
                'initial_capital': initial_capital,
                'current_value': current_value,
                'total_profit': total_profit,
                'roi': roi,
                'total_trades': total_trades,
                'recent_errors': recent_errors,
                'created_at': created_at
            })
        
        cur.close()
        conn.close()
        return users
        
    except Exception as e:
        print(f"Error in get_all_users_with_status: {e}")
        cur.close()
        conn.close()
        return []


def get_recent_errors(hours: int = 24) -> List[Dict]:
    """Get recent errors from error_logs"""
    if not table_exists('error_logs'):
        return []
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT timestamp, api_key, error_type, error_message
            FROM error_logs WHERE timestamp > NOW() - INTERVAL '%s hours'
            ORDER BY timestamp DESC LIMIT 50
        """, (hours,))
        
        errors = []
        for row in cur.fetchall():
            errors.append({
                'timestamp': row[0].strftime('%Y-%m-%d %H:%M:%S'),
                'api_key': row[1][:15] + '...' if row[1] else 'N/A',
                'error_type': row[2],
                'error_message': row[3]
            })
        cur.close()
        conn.close()
        return errors
    except:
        return []


def get_stats_summary() -> Dict:
    """
    Get summary statistics
    
    ═══════════════════════════════════════════════════════════════
    FORMULAS:
    ═══════════════════════════════════════════════════════════════
    Total Users       = COUNT(*) FROM follower_users
    Setup Completed   = COUNT(*) WHERE credentials_set = true
    Setup Rate        = (setup_completed / total_users) × 100%
    
    Active Now        = Users with heartbeat in last 5 minutes
    Active Rate       = (active_now / setup_completed) × 100%
    
    Total Trades      = COUNT(*) FROM portfolio_trades
    Total Profit      = SUM(pnl_usd) FROM portfolio_trades
    Avg Profit/User   = total_profit / setup_completed
    
    Total Capital     = SUM(initial_capital) FROM portfolio_users
    Current Value     = SUM(last_known_balance) FROM portfolio_users
    Platform ROI      = (total_profit / total_capital) × 100%
    ═══════════════════════════════════════════════════════════════
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    total_users = 0
    setup_completed = 0
    if table_exists('follower_users'):
        cur.execute("SELECT COUNT(*) FROM follower_users")
        total_users = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM follower_users WHERE credentials_set = true")
        setup_completed = cur.fetchone()[0] or 0
    
    active_now = 0
    if table_exists('agent_logs'):
        cur.execute("""
            SELECT COUNT(DISTINCT api_key) FROM agent_logs 
            WHERE event_type = 'heartbeat' AND timestamp > NOW() - INTERVAL '5 minutes'
        """)
        active_now = cur.fetchone()[0] or 0
    
    total_trades = 0
    total_profit = 0.0
    if table_exists('portfolio_trades'):
        cur.execute("SELECT COUNT(*), COALESCE(SUM(pnl_usd), 0) FROM portfolio_trades")
        row = cur.fetchone()
        total_trades = row[0] or 0
        total_profit = float(row[1] or 0)
    
    total_capital = 0.0
    current_value = 0.0
    if table_exists('portfolio_users'):
        cur.execute("SELECT COALESCE(SUM(initial_capital), 0), COALESCE(SUM(last_known_balance), 0) FROM portfolio_users")
        row = cur.fetchone()
        total_capital = float(row[0] or 0)
        current_value = float(row[1] or 0)
    
    recent_errors = 0
    if table_exists('error_logs'):
        cur.execute("SELECT COUNT(*) FROM error_logs WHERE timestamp > NOW() - INTERVAL '1 hour'")
        recent_errors = cur.fetchone()[0] or 0
    
    cur.close()
    conn.close()
    
    setup_rate = (setup_completed / total_users * 100) if total_users > 0 else 0
    active_rate = (active_now / setup_completed * 100) if setup_completed > 0 else 0
    avg_profit = total_profit / setup_completed if setup_completed > 0 else 0
    platform_roi = (total_profit / total_capital * 100) if total_capital > 0 else 0
    
    return {
        'total_users': total_users,
        'setup_completed': setup_completed,
        'setup_pending': total_users - setup_completed,
        'setup_rate': f"{setup_rate:.1f}%",
        'active_now': active_now,
        'active_rate': f"{active_rate:.1f}%",
        'total_trades': total_trades,
        'total_profit': total_profit,
        'avg_profit_per_user': avg_profit,
        'total_capital': total_capital,
        'current_value': current_value,
        'platform_roi': platform_roi,
        'recent_errors': recent_errors
    }


def log_error(api_key: str, error_type: str, error_message: str, context: Optional[Dict] = None):
    """Log an error for troubleshooting"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        import json
        cur.execute(
            "INSERT INTO error_logs (api_key, error_type, error_message, context) VALUES (%s, %s, %s, %s)",
            (api_key, error_type, error_message, json.dumps(context) if context else None)
        )
        conn.commit()
        cur.close()
        conn.close()
    except:
        pass


def log_agent_event(api_key: str, event_type: str, event_data: Optional[Dict] = None):
    """Log agent event (heartbeat, start, stop, trade, etc.)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        import json
        cur.execute(
            "INSERT INTO agent_logs (api_key, event_type, event_data) VALUES (%s, %s, %s)",
            (api_key, event_type, json.dumps(event_data) if event_data else None)
        )
        conn.commit()
        cur.close()
        conn.close()
    except:
        pass


def generate_admin_html(users: List[Dict], errors: List[Dict], stats: Dict) -> str:
    """Generate admin dashboard HTML"""
    
    user_rows = ""
    if not users:
        user_rows = "<tr><td colspan='8' style='text-align: center; padding: 40px; color: #6b7280;'>No users yet</td></tr>"
    else:
        for user in users:
            status_class = f"status-{user['agent_status']}"
            profit_class = "profit-positive" if user['total_profit'] >= 0 else "profit-negative"
            roi_class = "profit-positive" if user['roi'] >= 0 else "profit-negative"
            profit_str = f"+${user['total_profit']:.2f}" if user['total_profit'] >= 0 else f"-${abs(user['total_profit']):.2f}"
            roi_str = f"+{user['roi']:.1f}%" if user['roi'] >= 0 else f"{user['roi']:.1f}%"
            
            user_rows += f"""
            <tr>
                <td><span class="status-badge {status_class}">{user['status_emoji']} {user['status_text']}</span></td>
                <td>{user['email']}</td>
                <td class="api-key">{user['api_key'][:15]}...</td>
                <td>${user['initial_capital']:,.2f}</td>
                <td>{user['total_trades']}</td>
                <td class="{profit_class}">{profit_str}</td>
                <td class="{roi_class}">{roi_str}</td>
                <td>{'⚠️ ' + str(user['recent_errors']) if user['recent_errors'] > 0 else '✅'}</td>
            </tr>"""
    
    error_items = ""
    if not errors:
        error_items = "<div style='text-align: center; padding: 40px; color: #10b981;'>No errors in last 24h 🎉</div>"
    else:
        for error in errors[:20]:
            error_items += f"""
            <div class="error-item">
                <div class="error-header">
                    <span class="error-type">{error['error_type']}</span>
                    <span class="error-timestamp">{error['timestamp']}</span>
                </div>
                <div class="error-message">{error['error_message'][:300]}</div>
            </div>"""
    
    profit_color = "#10b981" if stats['total_profit'] >= 0 else "#ef4444"
    roi_color = "#10b981" if stats['platform_roi'] >= 0 else "#ef4444"
    profit_str = f"+${stats['total_profit']:,.2f}" if stats['total_profit'] >= 0 else f"-${abs(stats['total_profit']):,.2f}"
    roi_str = f"+{stats['platform_roi']:.1f}%" if stats['platform_roi'] >= 0 else f"{stats['platform_roi']:.1f}%"
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>🚀 $NIKEPIG Admin</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; padding: 20px; color: #e5e7eb; }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        .header {{ background: rgba(255,255,255,0.1); border-radius: 16px; padding: 30px; margin-bottom: 20px; }}
        h1 {{ color: #667eea; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; }}
        .stat-label {{ color: #9ca3af; font-size: 12px; text-transform: uppercase; }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #fff; }}
        .stat-detail {{ font-size: 12px; color: #6b7280; margin-top: 5px; }}
        .section {{ background: rgba(255,255,255,0.05); border-radius: 16px; padding: 25px; margin-bottom: 20px; }}
        .section h2 {{ color: #667eea; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: rgba(102, 126, 234, 0.2); padding: 14px; text-align: left; color: #667eea; font-size: 12px; text-transform: uppercase; }}
        td {{ padding: 14px; border-bottom: 1px solid rgba(255,255,255,0.05); }}
        .status-badge {{ padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
        .status-active {{ background: rgba(16, 185, 129, 0.2); color: #10b981; }}
        .status-ready {{ background: rgba(245, 158, 11, 0.2); color: #f59e0b; }}
        .status-idle {{ background: rgba(249, 115, 22, 0.2); color: #f97316; }}
        .status-pending {{ background: rgba(107, 114, 128, 0.2); color: #9ca3af; }}
        .profit-positive {{ color: #10b981; font-weight: 600; }}
        .profit-negative {{ color: #ef4444; font-weight: 600; }}
        .api-key {{ font-family: monospace; font-size: 12px; color: #6b7280; }}
        .error-item {{ border-left: 4px solid #ef4444; background: rgba(239, 68, 68, 0.1); padding: 15px; margin-bottom: 12px; border-radius: 8px; }}
        .error-header {{ display: flex; gap: 15px; margin-bottom: 8px; }}
        .error-type {{ font-weight: 600; color: #ef4444; }}
        .error-timestamp {{ color: #6b7280; font-size: 12px; }}
        .error-message {{ color: #fca5a5; font-size: 13px; }}
        .refresh-btn {{ background: #667eea; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; }}
        .refresh-btn:hover {{ background: #5568d3; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1>🚀 $NIKEPIG Admin Dashboard</h1>
                    <p style="color: #9ca3af; margin-top: 5px;">{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                </div>
                <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Users</div>
                <div class="stat-value">{stats['total_users']}</div>
                <div class="stat-detail">{stats['setup_completed']} configured</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Active Now</div>
                <div class="stat-value" style="color: #10b981">{stats['active_now']}</div>
                <div class="stat-detail">{stats['active_rate']} of configured</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Trades</div>
                <div class="stat-value">{stats['total_trades']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Profit</div>
                <div class="stat-value" style="color: {profit_color}">{profit_str}</div>
                <div class="stat-detail">${stats['avg_profit_per_user']:.2f} avg/user</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Platform Capital</div>
                <div class="stat-value">${stats['total_capital']:,.0f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Current Value</div>
                <div class="stat-value">${stats['current_value']:,.0f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Platform ROI</div>
                <div class="stat-value" style="color: {roi_color}">{roi_str}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Errors (1h)</div>
                <div class="stat-value" style="color: {'#ef4444' if stats['recent_errors'] > 0 else '#10b981'}">{stats['recent_errors']}</div>
            </div>
        </div>
        
        <div class="section">
            <h2>👥 Users ({stats['total_users']})</h2>
            <table>
                <thead><tr><th>Status</th><th>Email</th><th>API Key</th><th>Capital</th><th>Trades</th><th>Profit</th><th>ROI</th><th>Errors</th></tr></thead>
                <tbody>{user_rows}</tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>⚠️ Recent Errors (24h)</h2>
            {error_items}
        </div>
    </div>
    <script>setTimeout(() => location.reload(), 60000);</script>
</body>
</html>"""
