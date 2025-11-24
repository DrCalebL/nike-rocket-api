"""
Nike Rocket Position Monitor
=============================

Monitors open positions for TP/SL fills and records actual P&L.

This ensures:
- Accurate profit tracking (uses real fill prices, not signals)
- Fair billing (users only pay on actual profits)
- Dashboard accuracy (shows real trading results)

Flow:
1. Hosted trading loop places orders → saves to open_positions table
2. Position monitor runs every 60 seconds
3. Checks each open position against Kraken
4. When TP or SL fills → calculates real P&L → records in trades table
5. Updates user statistics
6. Removes from open_positions

Author: Nike Rocket Team
Created: November 24, 2025
"""

import asyncio
import logging
import os
import secrets
from datetime import datetime
from typing import Optional, Dict, Any

import ccxt
from cryptography.fernet import Fernet

# Configuration
CHECK_INTERVAL_SECONDS = 60  # Check every minute
FEE_PERCENTAGE = 0.10  # 10% of profits

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("POSITION_MONITOR")

# Encryption for credentials
ENCRYPTION_KEY = os.getenv("CREDENTIALS_ENCRYPTION_KEY")
cipher = Fernet(ENCRYPTION_KEY.encode()) if ENCRYPTION_KEY else None


class PositionMonitor:
    """
    Monitors open positions and records actual P&L when they close.
    """
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.logger = logger
        self.active_exchanges: Dict[str, ccxt.krakenfutures] = {}
    
    def decrypt_credentials(self, encrypted_key: str, encrypted_secret: str):
        """Decrypt Kraken API credentials"""
        if not cipher:
            return None, None
        try:
            api_key = cipher.decrypt(encrypted_key.encode()).decode()
            api_secret = cipher.decrypt(encrypted_secret.encode()).decode()
            return api_key, api_secret
        except Exception:
            return None, None
    
    def get_exchange(self, user_api_key: str, kraken_key: str, kraken_secret: str) -> Optional[ccxt.krakenfutures]:
        """Get or create exchange instance for user"""
        if user_api_key in self.active_exchanges:
            return self.active_exchanges[user_api_key]
        
        try:
            exchange = ccxt.krakenfutures({
                'apiKey': kraken_key,
                'secret': kraken_secret,
                'enableRateLimit': True,
            })
            self.active_exchanges[user_api_key] = exchange
            return exchange
        except Exception as e:
            self.logger.error(f"Failed to create exchange: {e}")
            return None
    
    async def get_open_positions(self) -> list:
        """Fetch all open positions from database"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    op.id,
                    op.user_id,
                    op.signal_id,
                    op.entry_order_id,
                    op.tp_order_id,
                    op.sl_order_id,
                    op.symbol,
                    op.kraken_symbol,
                    op.side,
                    op.quantity,
                    op.leverage,
                    op.entry_fill_price,
                    op.target_tp,
                    op.target_sl,
                    op.opened_at,
                    u.api_key as user_api_key,
                    u.kraken_api_key_encrypted,
                    u.kraken_api_secret_encrypted
                FROM open_positions op
                JOIN follower_users u ON op.user_id = u.id
                WHERE op.status = 'open'
            """)
            return [dict(row) for row in rows]
    
    async def check_order_status(self, exchange: ccxt.krakenfutures, order_id: str, symbol: str) -> Dict[str, Any]:
        """Check if an order has filled"""
        try:
            order = exchange.fetch_order(order_id, symbol)
            return {
                'status': order.get('status'),  # 'open', 'closed', 'canceled'
                'filled': order.get('filled', 0),
                'average': order.get('average'),  # Fill price
                'timestamp': order.get('timestamp')
            }
        except Exception as e:
            self.logger.error(f"Error checking order {order_id}: {e}")
            return {'status': 'unknown', 'error': str(e)}
    
    async def record_trade(self, position: dict, exit_price: float, exit_type: str, closed_at: datetime):
        """Record completed trade in database"""
        try:
            # Calculate P&L
            entry_price = position['entry_fill_price']
            quantity = position['quantity']
            side = position['side']
            
            # P&L calculation
            if side == 'BUY':
                # Long: profit = (exit - entry) * quantity
                profit_usd = (exit_price - entry_price) * quantity
            else:
                # Short: profit = (entry - exit) * quantity
                profit_usd = (entry_price - exit_price) * quantity
            
            profit_percent = (profit_usd / (entry_price * quantity)) * 100 if entry_price > 0 else 0
            
            # Calculate fee (10% of profit, only if profitable)
            fee_charged = max(0, profit_usd * FEE_PERCENTAGE)
            
            # Generate trade ID
            trade_id = f"trade_{secrets.token_urlsafe(12)}"
            
            async with self.db_pool.acquire() as conn:
                # Insert trade record
                await conn.execute("""
                    INSERT INTO trades 
                    (user_id, signal_id, trade_id, kraken_order_id,
                     opened_at, closed_at, symbol, side,
                     entry_price, exit_price, position_size, leverage,
                     profit_usd, profit_percent, fee_charged, notes)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                """,
                    position['user_id'],
                    position['signal_id'],
                    trade_id,
                    position['entry_order_id'],
                    position['opened_at'],
                    closed_at,
                    position['symbol'],
                    side,
                    entry_price,
                    exit_price,
                    quantity,
                    position['leverage'],
                    profit_usd,
                    profit_percent,
                    fee_charged,
                    f"Closed by {exit_type}"
                )
                
                # Update user statistics
                await conn.execute("""
                    UPDATE follower_users 
                    SET 
                        total_profit = total_profit + $1,
                        total_trades = total_trades + 1,
                        monthly_profit = monthly_profit + $1,
                        monthly_trades = monthly_trades + 1,
                        monthly_fee_due = monthly_fee_due + $2
                    WHERE id = $3
                """, profit_usd, fee_charged, position['user_id'])
                
                # Mark position as closed
                await conn.execute("""
                    UPDATE open_positions SET status = 'closed' WHERE id = $1
                """, position['id'])
            
            # Log result
            emoji = "🟢" if profit_usd >= 0 else "🔴"
            self.logger.info(f"{emoji} Trade closed: {position['symbol']} {side}")
            self.logger.info(f"   Entry: ${entry_price:.2f} → Exit: ${exit_price:.2f}")
            self.logger.info(f"   P&L: ${profit_usd:+.2f} ({profit_percent:+.2f}%)")
            if fee_charged > 0:
                self.logger.info(f"   Fee: ${fee_charged:.2f} (10% of profit)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error recording trade: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def check_position(self, position: dict):
        """Check a single position for TP/SL fill"""
        user_short = position['user_api_key'][:15] + "..."
        
        try:
            # Decrypt credentials
            kraken_key, kraken_secret = self.decrypt_credentials(
                position['kraken_api_key_encrypted'],
                position['kraken_api_secret_encrypted']
            )
            
            if not kraken_key:
                self.logger.error(f"❌ {user_short}: Cannot decrypt credentials")
                return
            
            # Get exchange instance
            exchange = self.get_exchange(position['user_api_key'], kraken_key, kraken_secret)
            if not exchange:
                return
            
            kraken_symbol = position['kraken_symbol']
            
            # Check TP order
            tp_status = await self.check_order_status(exchange, position['tp_order_id'], kraken_symbol)
            
            if tp_status['status'] == 'closed':
                # TP filled!
                exit_price = tp_status.get('average', position['target_tp'])
                closed_at = datetime.fromtimestamp(tp_status['timestamp'] / 1000) if tp_status.get('timestamp') else datetime.now()
                
                self.logger.info(f"🎯 {user_short}: TP HIT on {position['symbol']}")
                await self.record_trade(position, exit_price, 'TP', closed_at)
                
                # Cancel SL order (no longer needed)
                try:
                    exchange.cancel_order(position['sl_order_id'], kraken_symbol)
                    self.logger.info(f"   ✅ Cancelled SL order")
                except Exception as e:
                    self.logger.warning(f"   ⚠️ Could not cancel SL: {e}")
                
                return
            
            # Check SL order
            sl_status = await self.check_order_status(exchange, position['sl_order_id'], kraken_symbol)
            
            if sl_status['status'] == 'closed':
                # SL filled!
                exit_price = sl_status.get('average', position['target_sl'])
                closed_at = datetime.fromtimestamp(sl_status['timestamp'] / 1000) if sl_status.get('timestamp') else datetime.now()
                
                self.logger.info(f"🛑 {user_short}: SL HIT on {position['symbol']}")
                await self.record_trade(position, exit_price, 'SL', closed_at)
                
                # Cancel TP order (no longer needed)
                try:
                    exchange.cancel_order(position['tp_order_id'], kraken_symbol)
                    self.logger.info(f"   ✅ Cancelled TP order")
                except Exception as e:
                    self.logger.warning(f"   ⚠️ Could not cancel TP: {e}")
                
                return
            
            # Check if both orders are canceled (manual close or liquidation)
            if tp_status['status'] == 'canceled' and sl_status['status'] == 'canceled':
                self.logger.warning(f"⚠️ {user_short}: Both TP/SL canceled for {position['symbol']} - marking as error")
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE open_positions SET status = 'error' WHERE id = $1",
                        position['id']
                    )
                return
            
            # Position still open, no action needed
            
        except Exception as e:
            self.logger.error(f"❌ Error checking position {position['id']}: {e}")
    
    async def check_all_positions(self):
        """Check all open positions"""
        positions = await self.get_open_positions()
        
        if not positions:
            return
        
        self.logger.debug(f"📊 Checking {len(positions)} open positions...")
        
        for position in positions:
            await self.check_position(position)
            # Small delay between checks to avoid rate limits
            await asyncio.sleep(0.5)
    
    async def run(self):
        """Main loop - checks positions every 60 seconds"""
        self.logger.info("=" * 60)
        self.logger.info("📊 POSITION MONITOR STARTED")
        self.logger.info("=" * 60)
        self.logger.info(f"🔄 Check interval: {CHECK_INTERVAL_SECONDS} seconds")
        self.logger.info(f"💰 Fee percentage: {FEE_PERCENTAGE*100:.0f}% of profits")
        self.logger.info("=" * 60)
        
        check_count = 0
        last_status_log = datetime.now()
        
        while True:
            try:
                check_count += 1
                
                await self.check_all_positions()
                
                # Log status every 5 minutes
                if (datetime.now() - last_status_log).total_seconds() >= 300:
                    positions = await self.get_open_positions()
                    self.logger.info(f"💓 Position monitor alive - Check #{check_count}, {len(positions)} open positions")
                    last_status_log = datetime.now()
                
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
                
            except asyncio.CancelledError:
                self.logger.info("🛑 Position monitor cancelled")
                break
                
            except Exception as e:
                self.logger.error(f"❌ Error in position monitor: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(10)


async def start_position_monitor(db_pool):
    """
    Start the position monitor.
    
    Call this from main.py startup:
    
    ```python
    from position_monitor import start_position_monitor
    
    @app.on_event("startup")
    async def startup_event():
        ...
        asyncio.create_task(start_position_monitor(db_pool))
    ```
    """
    # Wait for other systems to initialize
    await asyncio.sleep(40)
    
    logger.info("🚀 Starting position monitor...")
    
    monitor = PositionMonitor(db_pool)
    await monitor.run()
