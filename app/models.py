from enum import Enum
from datetime import datetime, date
from pydantic import BaseModel
from typing import Optional

# Enums
class UserPlan(str, Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"

class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"

class GoalPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class InvestmentType(str, Enum):
    STOCKS = "stocks"
    BONDS = "bonds"
    CRYPTO = "crypto"
    REAL_ESTATE = "real_estate"
    FUNDS = "funds"
    OTHERS = "others"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PENDING = "pending"

class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    PIX = "pix"
    BANK_TRANSFER = "bank_transfer"

# Models
class User(BaseModel):
    id: str
    email: str
    name: str
    password_hash: Optional[str] = None  
    created_at: Optional[datetime] = None
    plan: UserPlan = UserPlan.FREE
    email_confirmed: bool = False
    subscription_id: Optional[str] = None
    currency: Optional[str] = "R$"
    risk_profile: Optional[str] = "moderate"
    notification_pref: Optional[bool] = True
    stripe_customer_id: Optional[str] = None

    class Config:
        extra = "allow"  # Permite campos extras no modelo

    user_metadata: Optional[dict] = None  # Adicione este campo

class Transaction(BaseModel):
    id: str
    user_id: str
    type: TransactionType
    amount: float
    category: str
    description: Optional[str] = None
    date: date
    recurring: Optional[bool] = False

class Goal(BaseModel):
    id: str
    user_id: str
    name: str
    target_amount: float
    current_amount: Optional[float] = 0.0
    target_date: date
    priority: GoalPriority = GoalPriority.MEDIUM

class Investment(BaseModel):
    id: str
    user_id: str
    name: str
    type: InvestmentType
    amount: float
    expected_return: float
    date: date
    notes: Optional[str] = None

class Budget(BaseModel):
    id: str
    user_id: str
    category: str
    amount: float
    month: int
    year: int

class Notification(BaseModel):
    id: str
    user_id: str
    message: str
    date: Optional[datetime] = None
    read: Optional[bool] = False

class Subscription(BaseModel):
    id: str
    user_id: str
    plan: UserPlan
    status: SubscriptionStatus
    start_date: datetime
    end_date: Optional[datetime] = None
    payment_method: PaymentMethod
    stripe_subscription_id: Optional[str] = None