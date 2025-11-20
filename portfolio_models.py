"""
Nike Rocket - Portfolio Tracking Models
========================================
Database models for portfolio tracking system.

Author: Nike Rocket Team
Updated: November 20, 2025
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """
    User model for portfolio tracking
    Links to follower system users via api_key
    """
    __tablename__ = "portfolio_users"
    
    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String, unique=True, index=True, nullable=False)
    
    # Portfolio settings
    initial_capital = Column(Float, default=0.0)
    current_balance = Column(Float, default=0.0)
    total_deposits = Column(Float, default=0.0)
    total_withdrawals = Column(Float, default=0.0)
    
    # Tracking
    started_tracking_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    deposit_events = relationship("DepositEvent", back_populates="user", cascade="all, delete-orphan")
    withdrawal_events = relationship("WithdrawalEvent", back_populates="user", cascade="all, delete-orphan")


class Trade(Base):
    """
    Individual trade record
    """
    __tablename__ = "portfolio_trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("portfolio_users.id"), nullable=False)
    
    # Trade details
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)  # 'BUY' or 'SELL'
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    leverage = Column(Float, default=1.0)
    
    # Timing
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=False)
    
    # P&L
    pnl_usd = Column(Float, nullable=False)
    pnl_percent = Column(Float)
    
    # Account state at entry
    account_balance_at_entry = Column(Float)
    
    # Result
    status = Column(String, nullable=False)  # 'WIN' or 'LOSS'
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="trades")


class DepositEvent(Base):
    """
    Capital deposit event
    """
    __tablename__ = "portfolio_deposits"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("portfolio_users.id"), nullable=False)
    
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    note = Column(String)
    
    # Relationships
    user = relationship("User", back_populates="deposit_events")


class WithdrawalEvent(Base):
    """
    Capital withdrawal event
    """
    __tablename__ = "portfolio_withdrawals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("portfolio_users.id"), nullable=False)
    
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    note = Column(String)
    
    # Relationships
    user = relationship("User", back_populates="withdrawal_events")


def init_portfolio_db(engine):
    """Initialize portfolio database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Portfolio database tables created")
