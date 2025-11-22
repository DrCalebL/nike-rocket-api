"""
Admin Dashboard - COMPLETE VERSION with Trades Table
=====================================================
Full monitoring + trading data + profit tracking
"""

import os
import psycopg2
from datetime import datetime, timedelta
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


def get_agent_status(api_key: str, cur) -> Dict:
    """
    Deduce agent status from logs and errors
    
    Returns status based on:
    - Recent heartbeats
    - Kraken auth success/failure
    - Trade activity
    - Error patterns
    """
    
    # Check for recent heartbeat (agent alive?)
    cur.execute("""
        SELECT timestamp 
        FROM agent_logs 
        WHERE api_key = %s AND event_type = 'heartbeat'
        ORDER BY timestamp DESC 
        LIMIT 1
    """, (api_key,))
    
    heartbeat_row = cur.fetchone()
    last_heartbeat = heartbeat_row[0] if heartbeat_row else None
    
    # Check for Kraken auth success
    cur.execute("""
        SELECT timestamp 
        FROM agent_logs 
        WHERE api_key = %s AND event_type = 'kraken_auth_success'
        ORDER BY timestamp DESC 
        LIMIT 1
    """, (api_key,))
    
    auth_success_row = cur.fetchone()
    last_auth_success = auth_success_row[0] if auth_success_row else None
    
    # Check for recent auth failures
    cur.execute("""
        SELECT COUNT(*) 
        FROM error_logs 
        WHERE api_key = %s 
        AND error_type = 'kraken_auth_failed'
        AND timestamp > NOW() - INTERVAL '1 hour'
    """, (api_key,))
    
    recent_auth_failures = cur.fetchone()[0]
    
    # Check for any trades (if table exists)
    if table_exists('trades'):
        cur.execute("""
            SELECT COUNT(*) 
            FROM trades 
            WHERE api_key = %s
        """, (api_key,))
        total_trades = cur.fetchone()[0]
    else:
        total_trades = 0
    
    # Deduce status
    now = datetime.utcnow()
    
    # Active: Heartbeat in last 5 minutes
    if last_heartbeat and (now - last_heartbeat).seconds < 300:
        if recent_auth_failures > 0:
            return {
                'status': 'error',
                'status_text': 'Auth Failed',
                'emoji': '❌',
                'detail': 'Kraken credentials invalid'
            }
        elif last_auth_success:
            return {
                'status': 'active',
                'status_text': 'Active',
                'emoji': '🟢',
                'detail': 'Agent running, Kraken connected'
            }
        else:
            return {
                'status': 'starting',
                'status_text': 'Starting',
                'emoji': '🟡',
                'detail': 'Agent starting up'
            }
    
    # Has trades but no recent heartbeat
    elif total_trades > 0:
        return {
            'status': 'inactive',
            'status_text': 'Inactive',
            'emoji': '🔴',
            'detail': 'Agent stopped (was working before)'
        }
    
    # Auth success but no heartbeat
    elif last_auth_success:
        return {
            'status': 'stopped',
            'status_text': 'Stopped',
            'emoji': '⏸️',
            'detail': 'Setup complete but agent stopped'
        }
    
    # Never authenticated
    else:
        return {
            'status': 'pending',
            'status_text': 'Setup Pending',
            'emoji': '⏳',
            'detail': 'User hasn\'t completed setup'
        }


def get_all_users_with_status() -> List[Dict]:
    """Get all users with intelligent status deduction + trade data"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get all users
    cur.execute("""
        SELECT email, api_key, created_at
        FROM users
        ORDER BY created_at DESC
    """)
    
    users = []
    for row in cur.fetchall():
        email, api_key, created_at = row
        
        # Get agent status from logs
        agent_status = get_agent_status(api_key, cur)
        
        # Get trade data (if table exists)
        if table_exists('trades'):
            cur.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    MAX(timestamp) as last_trade_at,
                    COALESCE(SUM(profit), 0) as total_profit
                FROM trades 
                WHERE api_key = %s
            """, (api_key,))
            
            trade_row = cur.fetchone()
            total_trades = trade_row[0] if trade_row else 0
            last_trade_at = trade_row[1] if trade_row else None
            total_profit = float(trade_row[2]) if trade_row else 0.0
        else:
            total_trades = 0
            last_trade_at = None
            total_profit = 0.0
        
        # Get error count
        cur.execute("""
            SELECT COUNT(*) 
            FROM error_logs 
            WHERE api_key = %s 
            AND timestamp > NOW() - INTERVAL '24 hours'
        """, (api_key,))
        recent_errors = cur.fetchone()[0]
        
        # Calculate time since last trade
        last_trade_str = "Never"
        if last_trade_at:
            delta = datetime.utcnow() - last_trade_at
            if delta.seconds < 3600:
                last_trade_str = f"{delta.seconds // 60}m ago"
            elif delta.seconds < 86400:
                last_trade_str = f"{delta.seconds // 3600}h ago"
            else:
                last_trade_str = f"{delta.days}d ago"
        
        users.append({
            'email': email,
            'api_key': api_key,
            'created_at': created_at,
            'agent_status': agent_status['status'],
            'status_text': agent_status['status_text'],
            'status_emoji': agent_status['emoji'],
            'status_detail': agent_status['detail'],
            'total_trades': total_trades,
            'last_trade_at': last_trade_at,
            'last_trade_str': last_trade_str,
            'total_profit': total_profit,
            'recent_errors': recent_errors
        })
    
    cur.close()
    conn.close()
    return users


def get_recent_errors(hours: int = 24) -> List[Dict]:
    """Get recent errors with context"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT e.timestamp, e.api_key, e.error_type, e.error_message, u.email
        FROM error_logs e
        LEFT JOIN users u ON e.api_key = u.api_key
        WHERE e.timestamp > NOW() - INTERVAL '%s hours'
        ORDER BY e.timestamp DESC
        LIMIT 50
    """, (hours,))
    
    errors = [{
        'timestamp': row[0],
        'api_key': row[1],
        'error_type': row[2],
        'error_message': row[3],
        'email': row[4] or 'Unknown'
    } for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    return errors


def get_stats_summary() -> Dict:
    """Get summary statistics based on intelligent status"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    
    # Count users with successful Kraken auth
    cur.execute("""
        SELECT COUNT(DISTINCT api_key) 
        FROM agent_logs 
        WHERE event_type = 'kraken_auth_success'
    """)
    setup_completed = cur.fetchone()[0]
    
    # Count agents with recent heartbeat (last 5 min)
    cur.execute("""
        SELECT COUNT(DISTINCT api_key) 
        FROM agent_logs 
        WHERE event_type = 'heartbeat' 
        AND timestamp > NOW() - INTERVAL '5 minutes'
    """)
    active_now = cur.fetchone()[0]
    
    # Get trade stats (if table exists)
    if table_exists('trades'):
        cur.execute("SELECT COUNT(*) FROM trades")
        total_trades = cur.fetchone()[0]
        
        cur.execute("SELECT COALESCE(SUM(profit), 0) FROM trades")
        total_profit = float(cur.fetchone()[0])
    else:
        total_trades = 0
        total_profit = 0.0
    
    # Count recent errors
    cur.execute("""
        SELECT COUNT(*) 
        FROM error_logs 
        WHERE timestamp > NOW() - INTERVAL '1 hour'
    """)
    recent_errors = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    return {
        'total_users': total_users,
        'setup_completed': setup_completed,
        'setup_pending': total_users - setup_completed,
        'setup_rate': f"{(setup_completed/total_users*100) if total_users > 0 else 0:.1f}%",
        'total_trades': total_trades,
        'active_now': active_now,
        'active_rate': f"{(active_now/setup_completed*100) if setup_completed > 0 else 0:.1f}%",
        'total_profit': total_profit,
        'avg_profit_per_user': total_profit / setup_completed if setup_completed > 0 else 0.0,
        'recent_errors': recent_errors
    }


def create_error_logs_table():
    """Create ALL necessary tables: error_logs, agent_logs, AND trades"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Error logs table
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
    
    # Agent logs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            api_key VARCHAR(100),
            event_type VARCHAR(100),
            event_data JSONB
        )
    """)
    
    # Trades table (NEW!)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            api_key VARCHAR(100),
            signal_id VARCHAR(100),
            symbol VARCHAR(20),
            action VARCHAR(10),
            entry_price DECIMAL(20, 8),
            exit_price DECIMAL(20, 8),
            quantity DECIMAL(20, 8),
            profit DECIMAL(20, 8),
            status VARCHAR(20),
            exchange VARCHAR(50)
        )
    """)
    
    # Indexes for error_logs
    cur.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp ON error_logs(timestamp DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_api_key ON error_logs(api_key)")
    
    # Indexes for agent_logs
    cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_timestamp ON agent_logs(timestamp DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_api_key ON agent_logs(api_key)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_event_type ON agent_logs(event_type)")
    
    # Indexes for trades
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_api_key ON trades(api_key)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_signal_id ON trades(signal_id)")
    
    conn.commit()
    cur.close()
    conn.close()


def log_error(api_key: str, error_type: str, error_message: str, context: Optional[Dict] = None):
    """Log error to error_logs table"""
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
    except Exception as e:
        print(f"❌ Failed to log error: {e}")


def log_agent_event(api_key: str, event_type: str, event_data: Optional[Dict] = None):
    """
    Log agent events to agent_logs table
    
    Event types:
    - 'heartbeat': Agent is alive
    - 'agent_started': Agent initialized
    - 'kraken_auth_success': Successfully authenticated with Kraken
    - 'trade_executed': Trade completed
    - 'signal_received': Received trading signal
    """
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
    except Exception as e:
        print(f"❌ Failed to log agent event: {e}")


def log_trade(api_key: str, signal_id: str, symbol: str, action: str, 
              entry_price: float, exit_price: float, quantity: float, 
              profit: float, status: str = 'completed', exchange: str = 'kraken'):
    """
    Log completed trade to trades table
    
    Args:
        api_key: User's API key
        signal_id: Signal ID from Nike Rocket
        symbol: Trading pair (e.g., 'ADAUSDT')
        action: 'BUY' or 'SELL'
        entry_price: Entry price
        exit_price: Exit price (TP or SL)
        quantity: Position size
        profit: Profit/loss in USD
        status: 'completed', 'stopped_out', 'took_profit'
        exchange: 'kraken', 'binance', etc.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO trades 
            (api_key, signal_id, symbol, action, entry_price, exit_price, 
             quantity, profit, status, exchange)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (api_key, signal_id, symbol, action, entry_price, exit_price, 
              quantity, profit, status, exchange))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Failed to log trade: {e}")


def generate_admin_html(users: List[Dict], errors: List[Dict], stats: Dict) -> str:
    """Generate admin dashboard HTML with full stats"""
    
    # User rows
    user_rows = ""
    if not users:
        user_rows = "<tr><td colspan='9' style='text-align: center; padding: 40px; color: #666;'>No users yet</td></tr>"
    else:
        for user in users:
            status_class = f"status-{user['agent_status']}"
            profit_class = "profit-positive" if user['total_profit'] >= 0 else "profit-negative"
            
            user_rows += f"""
            <tr>
                <td><span class="status-badge {status_class}" title="{user['status_detail']}">{user['status_emoji']} {user['status_text']}</span></td>
                <td>{user['email']}</td>
                <td class="api-key">{user['api_key'][:15]}...</td>
                <td class="timestamp">{user['created_at'].strftime('%Y-%m-%d %H:%M')}</td>
                <td>{user['total_trades']}</td>
                <td class="timestamp">{user['last_trade_str']}</td>
                <td class="{profit_class}">${user['total_profit']:.2f}</td>
                <td>{'⚠️ ' + str(user['recent_errors']) if user['recent_errors'] > 0 else '✅ 0'}</td>
            </tr>
            """
    
    # Error items
    error_items = ""
    if not errors:
        error_items = "<div style='text-align: center; padding: 40px; color: #666;'>No errors in last 24h 🎉</div>"
    else:
        for error in errors:
            error_items += f"""
            <div class="error-item">
                <div class="error-header">
                    <span class="error-type">{error['error_type']}</span>
                    <span class="error-timestamp">{error['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</span>
                </div>
                <div class="error-email">User: {error['email']} ({error['api_key'][:15]}...)</div>
                <div class="error-message">{error['error_message']}</div>
            </div>
            """
    
    profit_color = "#10b981" if stats['total_profit'] >= 0 else "#ef4444"
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>$NIKEPIG Admin - Complete Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1800px; margin: 0 auto; }}
        .header {{ background: white; border-radius: 12px; padding: 30px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        h1 {{ color: #667eea; margin-bottom: 5px; }}
        .subtitle {{ color: #666; font-size: 14px; }}
        .security-note {{ background: #d1fae5; border-left: 4px solid #10b981; padding: 12px; border-radius: 4px; margin-top: 10px; font-size: 13px; color: #065f46; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        .stat-label {{ color: #666; font-size: 13px; margin-bottom: 8px; text-transform: uppercase; }}
        .stat-value {{ font-size: 36px; font-weight: bold; color: #333; }}
        .stat-subtext {{ color: #10b981; font-size: 14px; margin-top: 5px; font-weight: 600; }}
        .users-section {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 20px; overflow-x: auto; }}
        .section-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        h2 {{ color: #333; font-size: 20px; }}
        .refresh-btn {{ background: #10b981; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 600; cursor: pointer; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #f9fafb; padding: 12px; text-align: left; font-weight: 600; color: #333; border-bottom: 2px solid #e5e7eb; font-size: 13px; }}
        td {{ padding: 12px; border-bottom: 1px solid #e5e7eb; font-size: 14px; }}
        tr:hover {{ background: #f9fafb; }}
        .status-badge {{ display: inline-flex; align-items: center; gap: 5px; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; cursor: help; }}
        .status-active {{ background: #d1fae5; color: #065f46; }}
        .status-starting {{ background: #fef3c7; color: #92400e; }}
        .status-stopped {{ background: #e0e7ff; color: #3730a3; }}
        .status-inactive {{ background: #fee2e2; color: #991b1b; }}
        .status-error {{ background: #fef2f2; color: #991b1b; }}
        .status-pending {{ background: #e5e7eb; color: #374151; }}
        .profit-positive {{ color: #10b981; font-weight: 600; }}
        .profit-negative {{ color: #ef4444; font-weight: 600; }}
        .errors-section {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        .error-item {{ border-left: 4px solid #ef4444; background: #fef2f2; padding: 15px; margin-bottom: 12px; border-radius: 4px; }}
        .error-header {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
        .error-type {{ font-weight: 600; color: #991b1b; }}
        .error-timestamp {{ font-size: 12px; color: #666; }}
        .error-email {{ font-size: 12px; color: #666; margin-bottom: 5px; }}
        .error-message {{ color: #991b1b; font-size: 13px; }}
        .api-key {{ font-family: 'Courier New', monospace; font-size: 12px; color: #666; }}
        .timestamp {{ font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 $NIKEPIG's Massive Rocket - Complete Dashboard</h1>
            <p class="subtitle">Agent Monitoring + Trading Data | Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <div class="security-note">
                🔒 <strong>Smart Monitoring:</strong> Status from logs, profits from trades table. NO credentials stored!
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Signups</div>
                <div class="stat-value">{stats['total_users']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Setup Completed</div>
                <div class="stat-value">{stats['setup_completed']}</div>
                <div class="stat-subtext">{stats['setup_rate']} completion</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Active Now</div>
                <div class="stat-value" style="color: #10b981">{stats['active_now']}</div>
                <div class="stat-subtext">Heartbeat &lt; 5 min</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Trades</div>
                <div class="stat-value">{stats['total_trades']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Profit</div>
                <div class="stat-value" style="color: {profit_color}">${stats['total_profit']:.2f}</div>
                <div class="stat-subtext">${stats['avg_profit_per_user']:.2f} avg/user</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Recent Errors</div>
                <div class="stat-value" style="color: {'#ef4444' if stats['recent_errors'] > 0 else '#10b981'}">{stats['recent_errors']}</div>
                <div class="stat-subtext">Last hour</div>
            </div>
        </div>
        
        <div class="users-section">
            <div class="section-header">
                <h2>👥 All Users ({stats['total_users']})</h2>
                <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Agent Status</th>
                        <th>Email</th>
                        <th>API Key</th>
                        <th>Signed Up</th>
                        <th>Trades</th>
                        <th>Last Trade</th>
                        <th>Profit</th>
                        <th>Errors (24h)</th>
                    </tr>
                </thead>
                <tbody>{user_rows}</tbody>
            </table>
        </div>
        
        <div class="errors-section">
            <div class="section-header">
                <h2>⚠️ Recent Errors (24h)</h2>
            </div>
            {error_items}
        </div>
    </div>
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>"""
