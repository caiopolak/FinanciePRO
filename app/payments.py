import stripe
import os
from typing import Optional, Dict

from app.database import Database
from .models import UserPlan, SubscriptionStatus, PaymentMethod
from datetime import datetime, timedelta

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class PaymentService:
    def __init__(self, db: Database):
        self.db = db
        self.plans = {
            UserPlan.PRO.value: {
                "price_id": os.getenv("STRIPE_PRO_PRICE_ID"),
                "amount": 2900,  # R$29.00
                "currency": "brl",
                "interval": "month"
            },
            UserPlan.BUSINESS.value: {
                "price_id": os.getenv("STRIPE_BUSINESS_PRICE_ID"),
                "amount": 9900,  # R$99.00
                "currency": "brl",
                "interval": "month"
            }
        }
    
    def create_customer(self, user_id: str, email: str, name: str) -> Optional[str]:
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"user_id": user_id}
            )
            return customer.id
        except stripe.error.StripeError as e:
            print(f"Error creating Stripe customer: {e}")
            return None
    
    def create_subscription(self, user_id: str, email: str, name: str, plan: str, payment_method: str) -> Optional[Dict]:
        if plan not in self.plans:
            return {"error": "Invalid plan"}
        
        try:
            # Verificar se o usuário já é cliente no Stripe
            user = self.db.get_user_by_id(user_id)
            customer_id = None
            
            if user and hasattr(user, "stripe_customer_id") and user.stripe_customer_id:
                customer_id = user.stripe_customer_id
            else:
                # Criar novo cliente
                customer_id = self.create_customer(user_id, email, name)
                if not customer_id:
                    return {"error": "Failed to create customer"}
                
                # Atualizar usuário com stripe_customer_id
                self.db.update_user(user_id, stripe_customer_id=customer_id)
            
            # Criar assinatura no Stripe
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": self.plans[plan]["price_id"]}],
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"],
                metadata={
                    "user_id": user_id,
                    "plan": plan,
                    "payment_method": payment_method
                }
            )
            
            # Criar registro da assinatura no banco de dados
            subscription_data = self.db.create_subscription(
                user_id, 
                plan, 
                payment_method, 
                subscription.id
            )
            
            if "error" in subscription_data:
                return subscription_data
            
            return {
                "subscription_id": subscription.id,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret,
                "payment_intent_id": subscription.latest_invoice.payment_intent.id
            }
        except stripe.error.StripeError as e:
            print(f"Error creating subscription: {e}")
            return {"error": str(e)}
    
    def handle_webhook_event(self, payload: str, sig_header: str) -> bool:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
            )
            
            if event.type == "invoice.payment_succeeded":
                return self.handle_payment_succeeded(event)
            elif event.type == "invoice.payment_failed":
                return self.handle_payment_failed(event)
            elif event.type == "customer.subscription.deleted":
                return self.handle_subscription_canceled(event)
            
            return True
        except stripe.error.SignatureVerificationError as e:
            print(f"Webhook signature verification failed: {e}")
            return False
        except Exception as e:
            print(f"Error handling webhook event: {e}")
            return False
    
    def handle_payment_succeeded(self, event) -> bool:
        invoice = event.data.object
        subscription_id = invoice.subscription
        
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            user_id = subscription.metadata.get("user_id")
            plan = subscription.metadata.get("plan")
            
            if not user_id or not plan:
                return False
            
            # Atualizar assinatura no banco de dados
            updates = {
                "status": SubscriptionStatus.ACTIVE.value,
                "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
            }
            
            response = self.db.client.table("subscriptions").update(updates).eq("stripe_subscription_id", subscription_id).execute()
            
            if response.data:
                # Atualizar plano do usuário
                self.db.client.table("users").update({"plan": plan}).eq("id", user_id).execute()
                return True
            
            return False
        except Exception as e:
            print(f"Error handling payment succeeded: {e}")
            return False
    
    def handle_payment_failed(self, event) -> bool:
        invoice = event.data.object
        subscription_id = invoice.subscription
        
        try:
            # Atualizar status da assinatura para expirado
            response = self.db.client.table("subscriptions").update({
                "status": SubscriptionStatus.EXPIRED.value
            }).eq("stripe_subscription_id", subscription_id).execute()
            
            if response.data:
                # Reverter usuário para plano free
                subscription = response.data[0]
                self.db.client.table("users").update({
                    "plan": UserPlan.FREE.value
                }).eq("id", subscription["user_id"]).execute()
                
                # Adicionar notificação
                self.db.add_notification(
                    subscription["user_id"],
                    "Seu pagamento falhou e sua assinatura foi cancelada. Atualize seu método de pagamento para continuar."
                )
                
                return True
            
            return False
        except Exception as e:
            print(f"Error handling payment failed: {e}")
            return False
    
    def handle_subscription_canceled(self, event) -> bool:
        subscription = event.data.object
        subscription_id = subscription.id
        
        try:
            # Atualizar status da assinatura para cancelado
            response = self.db.client.table("subscriptions").update({
                "status": SubscriptionStatus.CANCELED.value
            }).eq("stripe_subscription_id", subscription_id).execute()
            
            if response.data:
                # Reverter usuário para plano free
                subscription_data = response.data[0]
                self.db.client.table("users").update({
                    "plan": UserPlan.FREE.value
                }).eq("id", subscription_data["user_id"]).execute()
                
                return True
            
            return False
        except Exception as e:
            print(f"Error handling subscription canceled: {e}")
            return False
    
    def cancel_subscription(self, subscription_id: str) -> bool:
        try:
            # Cancelar no Stripe
            stripe.Subscription.delete(subscription_id)
            
            # Atualizar no banco de dados
            response = self.db.cancel_subscription(subscription_id)
                
            return response
        except stripe.error.StripeError as e:
            print(f"Error canceling subscription: {e}")
            return False
    
    def update_payment_method(self, user_id: str, payment_method_id: str) -> bool:
        try:
            user = self.db.get_user_by_id(user_id)
            if not user or not hasattr(user, "stripe_customer_id") or not user.stripe_customer_id:
                return False
            
            # Anexar novo método de pagamento ao cliente
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=user.stripe_customer_id
            )
            
            # Definir como padrão
            stripe.Customer.modify(
                user.stripe_customer_id,
                invoice_settings={
                    "default_payment_method": payment_method_id
                }
            )
            
            return True
        except stripe.error.StripeError as e:
            print(f"Error updating payment method: {e}")
            return False