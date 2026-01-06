"""
Nike Rocket Configuration
=========================

Centralized configuration for fee tiers, constants, and utility functions.
Single source of truth to avoid inconsistencies across files.

Author: Nike Rocket Team
Version: 1.0
"""

import os
from datetime import datetime, timezone
from typing import Optional

# =============================================================================
# FEE TIERS - Single Source of Truth
# =============================================================================

FEE_TIERS = {
    'team': {
        'rate': 0.00,
        'display': '🏠 Team (0%)',
        'description': 'Team members - no fees'
    },
    'vip': {
        'rate': 0.05,
        'display': '⭐ VIP (5%)',
        'description': 'VIP customers'
    },
    'standard': {
        'rate': 0.10,
        'display': '👤 Standard (10%)',
        'description': 'Standard customers'
    },
}

DEFAULT_TIER = 'standard'


def get_fee_rate(tier: Optional[str]) -> float:
    """
    Get fee rate for a tier, with fallback to default.
    
    Handles None, empty string, and invalid tier names.
    
    Args:
        tier: Tier name ('team', 'vip', 'standard') or None
        
    Returns:
        Fee rate as float (0.0 to 1.0)
    """
    if not tier or tier not in FEE_TIERS:
        return FEE_TIERS[DEFAULT_TIER]['rate']
    return FEE_TIERS[tier]['rate']


def get_tier_display(tier: Optional[str]) -> str:
    """
    Get display name for a tier.
    
    Args:
        tier: Tier name or None
        
    Returns:
        Display string with emoji and percentage
    """
    if not tier or tier not in FEE_TIERS:
        return FEE_TIERS[DEFAULT_TIER]['display']
    return FEE_TIERS[tier]['display']


def get_tier_percentage_str(tier: Optional[str]) -> str:
    """
    Get percentage string for a tier (e.g., '10%').
    
    Args:
        tier: Tier name or None
        
    Returns:
        Percentage string
    """
    rate = get_fee_rate(tier)
    return f"{int(rate * 100)}%"


def get_valid_tiers() -> list:
    """Get list of valid tier names."""
    return list(FEE_TIERS.keys())


# =============================================================================
# DATETIME UTILITIES - Standardized UTC handling
# =============================================================================

def utc_now() -> datetime:
    """
    Get current UTC time (timezone-aware).
    
    Use this instead of datetime.utcnow() for consistency.
    Note: datetime.utcnow() is deprecated in Python 3.12+
    
    Returns:
        Timezone-aware datetime in UTC
    """
    return datetime.now(timezone.utc)


def ensure_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure a datetime is timezone-aware (UTC).
    
    Args:
        dt: Datetime that may be naive or aware
        
    Returns:
        Timezone-aware datetime in UTC, or None if input is None
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert datetime to naive UTC (for PostgreSQL TIMESTAMP columns).
    
    Args:
        dt: Datetime that may be naive or aware
        
    Returns:
        Naive datetime in UTC, or None if input is None
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        # Convert to UTC then strip timezone
        dt = dt.astimezone(timezone.utc)
        return dt.replace(tzinfo=None)
    return dt


# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================

def is_production() -> bool:
    """Check if running in production environment."""
    env = os.getenv("ENVIRONMENT", "").lower()
    railway_env = os.getenv("RAILWAY_ENVIRONMENT", "").lower()
    
    return env == "production" or railway_env == "production" or bool(os.getenv("RAILWAY_PROJECT_ID"))


def get_admin_email() -> str:
    """Get admin email from environment with fallback."""
    return os.getenv("ADMIN_EMAIL", "calebws87@gmail.com")


# =============================================================================
# BILLING CONSTANTS
# =============================================================================

BILLING_CYCLE_DAYS = 30
PAYMENT_GRACE_DAYS = 7
REMINDER_DAYS = [3, 5, 7]  # Days after invoice to send reminders

# Error log limits
ERROR_MESSAGE_MAX_LENGTH = 1000  # Increased from 500 for better stack traces
ERROR_CONTEXT_MAX_LENGTH = 2000


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Fee tiers
    'FEE_TIERS',
    'DEFAULT_TIER',
    'get_fee_rate',
    'get_tier_display',
    'get_tier_percentage_str',
    'get_valid_tiers',
    
    # Datetime utilities
    'utc_now',
    'ensure_utc_aware',
    'to_naive_utc',
    
    # Environment
    'is_production',
    'get_admin_email',
    
    # Constants
    'BILLING_CYCLE_DAYS',
    'PAYMENT_GRACE_DAYS',
    'REMINDER_DAYS',
    'ERROR_MESSAGE_MAX_LENGTH',
    'ERROR_CONTEXT_MAX_LENGTH',
]
