from .models import (
    User, UserPlan, Transaction, TransactionType, 
    Goal, GoalPriority, Investment, InvestmentType,
    Budget, Notification, Subscription, SubscriptionStatus
)
import calendar
import os
from supabase import create_client, Client
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict

class Database:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Supabase URL and Key must be set in environment variables")
        self.client: Client = create_client(url, key)
    
    # Operações de usuário
    def create_user(self, email: str, password: str, name: str) -> Optional[User]:
        try:
            # Criar usuário no Auth
            auth_response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "name": name,
                        "plan": UserPlan.FREE.value
                    }
                }
            })
            
            if not auth_response.user:
                print("Auth response:", auth_response)
                return None
                
            # Criar registro na tabela users
            user_data = {
                "id": str(auth_response.user.id),
                "email": email,
                "name": name,
                "plan": UserPlan.FREE.value,
                "created_at": datetime.utcnow().isoformat(),
                "currency": "R$",
                "risk_profile": "moderate",
                "notification_pref": True
            }
            
            response = self.client.table("users").insert(user_data).execute()
            
            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            
            # Se não retornar dados, buscar usuário criado
            user = self.get_user_by_id(auth_response.user.id)
            if user:
                return user
                
            return None
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        try:
            response = self.client.table("users").select("*").eq("id", user_id).execute()
            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            return None
        except Exception as e:
            print(f"Error getting user by ID: {str(e)}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        try:
            response = self.client.table("users").select("*").eq("email", email).execute()
            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            return None
        except Exception as e:
            print(f"Error getting user by email: {str(e)}")
            return None
    
    def update_user(self, user_id: str, **kwargs) -> bool:
        try:
            # Remover campos que não devem ser atualizados
            restricted_fields = ['id', 'email', 'created_at']
            update_data = {k: v for k, v in kwargs.items() if k not in restricted_fields}
            
            response = self.client.table("users").update(update_data).eq("id", user_id).execute()
            return True if response.data else False
        except Exception as e:
            print(f"Error updating user: {str(e)}")
            return False
    
    # Operações de transação
    def add_transaction(self, user_id: str, transaction_data: Dict[str, Any]) -> Optional[Transaction]:
        try:
            # Verificar limite do plano
            if not self.check_plan_limits(user_id, "transactions"):
                return None
                
            # Validar dados
            required_fields = ['type', 'amount', 'date', 'category']
            if not all(field in transaction_data for field in required_fields):
                raise ValueError("Missing required transaction fields")
                
            transaction_data["user_id"] = user_id
            response = self.client.table("transactions").insert(transaction_data).execute()
            
            if response.data and len(response.data) > 0:
                return Transaction(**response.data[0])
            return None
        except Exception as e:
            print(f"Error adding transaction: {str(e)}")
            return None
    
    def get_transactions(self, user_id: str, month: int = None, year: int = None) -> List[Transaction]:
        query = self.client.table("transactions").select("*").eq("user_id", user_id)
        
        if month and year:
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]}"
            query = query.gte("date", start_date).lte("date", end_date)
        
        response = query.order("date", desc=True).execute()
        return [Transaction(**t) for t in response.data] if response.data else []
    
    def get_transaction_by_id(self, transaction_id: str) -> Optional[Transaction]:
        try:
            response = self.client.table("transactions").select("*").eq("id", transaction_id).execute()
            if response.data and len(response.data) > 0:
                return Transaction(**response.data[0])
            return None
        except Exception as e:
            print(f"Error getting transaction: {e}")
            return None
    
    def update_transaction(self, transaction_id: str, **kwargs) -> bool:
        try:
            response = self.client.table("transactions").update(kwargs).eq("id", transaction_id).execute()
            return True if response.data else False
        except Exception as e:
            print(f"Error updating transaction: {e}")
            return False
    
    def delete_transaction(self, transaction_id: str) -> bool:
        try:
            response = self.client.table("transactions").delete().eq("id", transaction_id).execute()
            return True if response.data else False
        except Exception as e:
            print(f"Error deleting transaction: {e}")
            return False
    
    def get_total_by_type(self, user_id: str, type_: str, month: int = None, year: int = None) -> float:
        query = self.client.table("transactions").select("amount").eq("user_id", user_id).eq("type", type_)
        
        if month and year:
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]}"
            query = query.gte("date", start_date).lte("date", end_date)
        
        response = query.execute()
        total = sum(t['amount'] for t in response.data) if response.data else 0.0
        return total
    
    def get_category_summary(self, user_id: str, type_: str, month: int = None, year: int = None) -> List[Dict]:
        query = self.client.table("transactions").select("category, amount").eq("user_id", user_id).eq("type", type_)
        
        if month and year:
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]}"
            query = query.gte("date", start_date).lte("date", end_date)
        
        response = query.execute()
        if not response.data:
            return []
        
        # Agrupar por categoria
        summary = {}
        for t in response.data:
            category = t['category']
            amount = t['amount']
            if category in summary:
                summary[category] += amount
            else:
                summary[category] = amount
        
        return [{"category": k, "sum": v} for k, v in summary.items()]
    
    # Operações de metas
    def add_goal(self, user_id: str, goal_data: Dict) -> Optional[Goal]:
        try:
            # Verificar limite do plano
            if not self.check_plan_limits(user_id, "goals"):
                return None
                
            goal_data["user_id"] = user_id
            response = self.client.table("goals").insert(goal_data).execute()
            return Goal(**response.data[0]) if response.data else None
        except Exception as e:
            print(f"Error adding goal: {e}")
            return None
    
    def get_goals(self, user_id: str) -> List[Goal]:
        response = self.client.table("goals").select("*").eq("user_id", user_id).order("priority", desc=True).execute()
        return [Goal(**g) for g in response.data] if response.data else []
    
    def get_goal_by_id(self, goal_id: str) -> Optional[Goal]:
        try:
            response = self.client.table("goals").select("*").eq("id", goal_id).execute()
            if response.data and len(response.data) > 0:
                return Goal(**response.data[0])
            return None
        except Exception as e:
            print(f"Error getting goal: {e}")
            return None
    
    def update_goal(self, goal_id: str, **kwargs) -> bool:
        try:
            response = self.client.table("goals").update(kwargs).eq("id", goal_id).execute()
            return True if response.data else False
        except Exception as e:
            print(f"Error updating goal: {e}")
            return False
    
    def update_goal_progress(self, goal_id: str, amount: float) -> bool:
        try:
            goal = self.get_goal_by_id(goal_id)
            if not goal:
                return False
                
            new_amount = goal.current_amount + amount
            response = self.client.table("goals").update({
                "current_amount": new_amount
            }).eq("id", goal_id).execute()
            return True if response.data else False
        except Exception as e:
            print(f"Error updating goal: {e}")
            return False
    
    def delete_goal(self, goal_id: str) -> bool:
        try:
            response = self.client.table("goals").delete().eq("id", goal_id).execute()
            return True if response.data else False
        except Exception as e:
            print(f"Error deleting goal: {e}")
            return False
    
    # Operações de investimentos
    def add_investment(self, user_id: str, investment_data: Dict) -> Optional[Investment]:
        try:
            investment_data["user_id"] = user_id
            response = self.client.table("investments").insert(investment_data).execute()
            return Investment(**response.data[0]) if response.data else None
        except Exception as e:
            print(f"Error adding investment: {e}")
            return None
    
    def get_investments(self, user_id: str) -> List[Investment]:
        response = self.client.table("investments").select("*").eq("user_id", user_id).order("date", desc=True).execute()
        return [Investment(**i) for i in response.data] if response.data else []
    
    def get_investment_by_id(self, investment_id: str) -> Optional[Investment]:
        try:
            response = self.client.table("investments").select("*").eq("id", investment_id).execute()
            if response.data and len(response.data) > 0:
                return Investment(**response.data[0])
            return None
        except Exception as e:
            print(f"Error getting investment: {e}")
            return None
    
    def update_investment(self, investment_id: str, **kwargs) -> bool:
        try:
            response = self.client.table("investments").update(kwargs).eq("id", investment_id).execute()
            return True if response.data else False
        except Exception as e:
            print(f"Error updating investment: {e}")
            return False
    
    def delete_investment(self, investment_id: str) -> bool:
        try:
            response = self.client.table("investments").delete().eq("id", investment_id).execute()
            return True if response.data else False
        except Exception as e:
            print(f"Error deleting investment: {e}")
            return False
    
    # Operações de orçamento
    def add_budget(self, user_id: str, budget_data: Dict) -> Optional[Budget]:
        try:
            budget_data["user_id"] = user_id
            response = self.client.table("budgets").insert(budget_data).execute()
            return Budget(**response.data[0]) if response.data else None
        except Exception as e:
            print(f"Error adding budget: {e}")
            return None
    
    def get_budgets(self, user_id: str, month: int = None, year: int = None) -> List[Budget]:
        query = self.client.table("budgets").select("*").eq("user_id", user_id)
        
        if month and year:
            query = query.eq("month", month).eq("year", year)
        
        response = query.execute()
        return [Budget(**b) for b in response.data] if response.data else []
    
    def get_budget_by_id(self, budget_id: str) -> Optional[Budget]:
        try:
            response = self.client.table("budgets").select("*").eq("id", budget_id).execute()
            if response.data and len(response.data) > 0:
                return Budget(**response.data[0])
            return None
        except Exception as e:
            print(f"Error getting budget: {e}")
            return None
    
    def update_budget(self, budget_id: str, **kwargs) -> bool:
        try:
            response = self.client.table("budgets").update(kwargs).eq("id", budget_id).execute()
            return True if response.data else False
        except Exception as e:
            print(f"Error updating budget: {e}")
            return False
    
    def delete_budget(self, budget_id: str) -> bool:
        try:
            response = self.client.table("budgets").delete().eq("id", budget_id).execute()
            return True if response.data else False
        except Exception as e:
            print(f"Error deleting budget: {e}")
            return False
    
    def check_budget_alerts(self, user_id: str, month: int, year: int) -> List[Dict]:
        budgets = self.get_budgets(user_id, month, year)
        transactions = self.get_transactions(user_id, month, year)
        
        alerts = []
        for budget in budgets:
            category_expenses = sum(
                t.amount for t in transactions 
                if t.type == TransactionType.EXPENSE and t.category == budget.category
            )
            
            percentage = (category_expenses / budget.amount) * 100 if budget.amount > 0 else 0
            
            if percentage > 100:
                alerts.append({
                    "category": budget.category,
                    "budget": budget.amount,
                    "spent": category_expenses,
                    "percentage": percentage,
                    "status": "danger"
                })
            elif percentage > 80:
                alerts.append({
                    "category": budget.category,
                    "budget": budget.amount,
                    "spent": category_expenses,
                    "percentage": percentage,
                    "status": "warning"
                })
        
        return alerts
    
    # Operações de notificação
    def add_notification(self, user_id: str, message: str) -> Optional[Notification]:
        try:
            notification_data = {
                "user_id": user_id,
                "message": message,
                "date": datetime.utcnow().isoformat()
            }
            
            response = self.client.table("notifications").insert(notification_data).execute()
            return Notification(**response.data[0]) if response.data else None
        except Exception as e:
            print(f"Error adding notification: {e}")
            return None
    
    def get_notifications(self, user_id: str, limit: int = 10) -> List[Notification]:
        response = self.client.table("notifications").select("*").eq("user_id", user_id).order("date", desc=True).limit(limit).execute()
        return [Notification(**n) for n in response.data] if response.data else []
    
    def get_unread_notifications(self, user_id: str) -> List[Notification]:
        response = self.client.table("notifications").select("*").eq("user_id", user_id).eq("read", False).order("date", desc=True).execute()
        return [Notification(**n) for n in response.data] if response.data else []
    
    def mark_notification_as_read(self, notification_id: str) -> bool:
        try:
            response = self.client.table("notifications").update({"read": True}).eq("id", notification_id).execute()
            return True if response.data else False
        except Exception as e:
            print(f"Error marking notification as read: {e}")
            return False
    
    # Operações de assinatura
    def create_subscription(self, user_id: str, plan: str, payment_method: str, stripe_subscription_id: str) -> Optional[Dict]:
        try:
            # Verificar se o usuário já tem uma assinatura ativa
            response = self.client.table("subscriptions").select("*").eq("user_id", user_id).eq("status", SubscriptionStatus.ACTIVE.value).execute()
            
            if response.data:
                return {"error": "User already has an active subscription"}
            
            # Criar nova assinatura
            subscription_data = {
                "user_id": user_id,
                "plan": plan,
                "status": SubscriptionStatus.ACTIVE.value,
                "start_date": datetime.utcnow().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "payment_method": payment_method,
                "stripe_subscription_id": stripe_subscription_id
            }
            
            response = self.client.table("subscriptions").insert(subscription_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating subscription: {e}")
            return None
    
    def update_subscription_status(self, subscription_id: str, status: str) -> bool:
        try:
            updates = {"status": status}
            
            if status == SubscriptionStatus.ACTIVE.value:
                updates["end_date"] = (datetime.utcnow() + timedelta(days=30)).isoformat()
            
            response = self.client.table("subscriptions").update(updates).eq("id", subscription_id).execute()
            return True if response.data else False
        except Exception as e:
            print(f"Error updating subscription status: {e}")
            return False
    
    def get_user_subscription(self, user_id: str) -> Optional[Dict]:
        response = self.client.table("subscriptions").select("*").eq("user_id", user_id).order("start_date", desc=True).limit(1).execute()
        return response.data[0] if response.data else None
    
    def cancel_subscription(self, subscription_id: str) -> bool:
        try:
            response = self.client.table("subscriptions").update({
                "status": SubscriptionStatus.CANCELED.value
            }).eq("id", subscription_id).execute()
            return True if response.data else False
        except Exception as e:
            print(f"Error canceling subscription: {e}")
            return False
    
    # Verificação de limites do plano
    def check_plan_limits(self, user_id: str, feature: str) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        if user.plan == UserPlan.FREE:
            if feature == "transactions":
                # Limite de 100 transações/mês para plano free
                today = datetime.utcnow()
                first_day = today.replace(day=1)
                last_day = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                
                response = self.client.table("transactions").select("id", count="exact").eq("user_id", user_id).gte("date", first_day.isoformat()).lte("date", last_day.isoformat()).execute()
                
                return response.count < 100 if response.count is not None else True
            elif feature == "goals":
                # Limite de 3 metas para plano free
                response = self.client.table("goals").select("id", count="exact").eq("user_id", user_id).execute()
                return response.count < 3 if response.count is not None else True
        
        return True