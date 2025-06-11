from flask import Blueprint, current_app, request, jsonify, session, send_file
from datetime import datetime, date
from app.payments import PaymentService
from app.models import *
from app.auth import verify_jwt_token, generate_jwt_token
import csv
from io import StringIO, BytesIO
import calendar

api_bp = Blueprint('api', __name__)

# Middleware para verificar token JWT
@api_bp.before_request
def before_request():
    exempt_endpoints = [
        'api.get_dashboard_summary', 
        'auth.login',
        'auth.register',
        'auth.forgot_password',
        'auth.reset_password',
        'api.refresh_token'  # <--- Adicionar este endpoint
    ]
    
    if request.endpoint in exempt_endpoints:
        return
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Unauthorized"}), 401
    
    token = auth_header.split(' ')[1]
    payload = verify_jwt_token(token)
    
    if not payload:
        return jsonify({"error": "Invalid or expired token"}), 401
    
    request.user_id = payload['sub']

# Rotas de autenticação
@api_bp.route('/refresh-token', methods=['POST'])
def refresh_token():
    try:
        # Gerar novo token JWT
        token = generate_jwt_token(request.user_id)
        return jsonify({"token": token}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Rotas de transações
@api_bp.route('/transactions', methods=['GET'])
def get_transactions():
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    transactions = current_app.db.get_transactions(request.user_id, month, year)
    return jsonify([t.dict() for t in transactions]), 200

@api_bp.route('/transactions', methods=['POST'])
def add_transaction():
    data = request.get_json()
    
    try:
        # Validar dados
        if not data.get('type') or not data.get('amount') or not data.get('category') or not data.get('date'):
            return jsonify({"error": "Missing required fields"}), 400
            
        transaction = current_app.db.add_transaction(request.user_id, data)
        if not transaction:
            return jsonify({"error": "Failed to add transaction or plan limit reached"}), 400
        
        return jsonify(transaction.dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/transactions/<transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    data = request.get_json()
    
    try:
        # Verificar se a transação pertence ao usuário
        transaction = current_app.db.get_transaction_by_id(transaction_id)
        if not transaction or transaction.user_id != request.user_id:
            return jsonify({"error": "Transaction not found"}), 404
        
        # Atualizar transação
        success = current_app.db.update_transaction(transaction_id, **data)
        if not success:
            return jsonify({"error": "Failed to update transaction"}), 500
        
        updated_transaction = current_app.db.get_transaction_by_id(transaction_id)
        return jsonify(updated_transaction.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/transactions/<transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    try:
        # Verificar se a transação pertence ao usuário
        transaction = current_app.db.get_transaction_by_id(transaction_id)
        if not transaction or transaction.user_id != request.user_id:
            return jsonify({"error": "Transaction not found"}), 404
        
        # Excluir transação
        success = current_app.db.delete_transaction(transaction_id)
        if not success:
            return jsonify({"error": "Failed to delete transaction"}), 500
            
        return jsonify({"message": "Transaction deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Rotas de metas
@api_bp.route('/goals', methods=['GET'])
def get_goals():
    goals = current_app.db.get_goals(request.user_id)
    return jsonify([g.dict() for g in goals]), 200

@api_bp.route('/goals', methods=['POST'])
def add_goal():
    data = request.get_json()
    
    try:
        # Verificar limite do plano
        if not current_app.db.check_plan_limits(request.user_id, "goals"):
            return jsonify({"error": "Plan limit reached for goals"}), 400
        
        # Validar dados
        if not data.get('name') or not data.get('target_amount') or not data.get('target_date'):
            return jsonify({"error": "Missing required fields"}), 400
            
        goal = current_app.db.add_goal(request.user_id, data)
        if not goal:
            return jsonify({"error": "Failed to add goal"}), 500
        
        return jsonify(goal.dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/goals/<goal_id>', methods=['PUT'])
def update_goal(goal_id):
    data = request.get_json()
    
    try:
        # Verificar se a meta pertence ao usuário
        goal = current_app.db.get_goal_by_id(goal_id)
        if not goal or goal.user_id != request.user_id:
            return jsonify({"error": "Goal not found"}), 404
        
        # Atualizar meta
        success = current_app.db.update_goal(goal_id, **data)
        if not success:
            return jsonify({"error": "Failed to update goal"}), 500
        
        updated_goal = current_app.db.get_goal_by_id(goal_id)
        return jsonify(updated_goal.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/goals/<goal_id>/progress', methods=['PUT'])
def update_goal_progress(goal_id):
    amount = request.get_json().get('amount')
    
    if not amount:
        return jsonify({"error": "Amount is required"}), 400
    
    try:
        # Verificar se a meta pertence ao usuário
        goal = current_app.db.get_goal_by_id(goal_id)
        if not goal or goal.user_id != request.user_id:
            return jsonify({"error": "Goal not found"}), 404
        
        # Atualizar progresso
        success = current_app.db.update_goal_progress(goal_id, amount)
        if not success:
            return jsonify({"error": "Failed to update goal progress"}), 500
        
        return jsonify({"message": "Goal progress updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/goals/<goal_id>', methods=['DELETE'])
def delete_goal(goal_id):
    try:
        # Verificar se a meta pertence ao usuário
        goal = current_app.db.get_goal_by_id(goal_id)
        if not goal or goal.user_id != request.user_id:
            return jsonify({"error": "Goal not found"}), 404
        
        # Excluir meta
        success = current_app.db.delete_goal(goal_id)
        if not success:
            return jsonify({"error": "Failed to delete goal"}), 500
            
        return jsonify({"message": "Goal deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Rotas de investimentos
@api_bp.route('/investments', methods=['GET'])
def get_investments():
    investments = current_app.db.get_investments(request.user_id)
    return jsonify([i.dict() for i in investments]), 200

@api_bp.route('/investments', methods=['POST'])
def add_investment():
    data = request.get_json()
    
    try:
        # Validar dados
        if not data.get('name') or not data.get('type') or not data.get('amount') or not data.get('date'):
            return jsonify({"error": "Missing required fields"}), 400
            
        investment = current_app.db.add_investment(request.user_id, data)
        if not investment:
            return jsonify({"error": "Failed to add investment"}), 500
        
        return jsonify(investment.dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/investments/<investment_id>', methods=['PUT'])
def update_investment(investment_id):
    data = request.get_json()
    
    try:
        # Verificar se o investimento pertence ao usuário
        investment = current_app.db.get_investment_by_id(investment_id)
        if not investment or investment.user_id != request.user_id:
            return jsonify({"error": "Investment not found"}), 404
        
        # Atualizar investimento
        success = current_app.db.update_investment(investment_id, **data)
        if not success:
            return jsonify({"error": "Failed to update investment"}), 500
        
        updated_investment = current_app.db.get_investment_by_id(investment_id)
        return jsonify(updated_investment.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/investments/<investment_id>', methods=['DELETE'])
def delete_investment(investment_id):
    try:
        # Verificar se o investimento pertence ao usuário
        investment = current_app.db.get_investment_by_id(investment_id)
        if not investment or investment.user_id != request.user_id:
            return jsonify({"error": "Investment not found"}), 404
        
        # Excluir investimento
        success = current_app.db.delete_investment(investment_id)
        if not success:
            return jsonify({"error": "Failed to delete investment"}), 500
            
        return jsonify({"message": "Investment deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Rotas de orçamentos
@api_bp.route('/budgets', methods=['GET'])
def get_budgets():
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    budgets = current_app.db.get_budgets(request.user_id, month, year)
    return jsonify([b.dict() for b in budgets]), 200

@api_bp.route('/budgets', methods=['POST'])
def add_budget():
    data = request.get_json()
    
    try:
        # Validar dados
        if not data.get('category') or not data.get('amount') or not data.get('month') or not data.get('year'):
            return jsonify({"error": "Missing required fields"}), 400
            
        budget = current_app.db.add_budget(request.user_id, data)
        if not budget:
            return jsonify({"error": "Failed to add budget"}), 500
        
        return jsonify(budget.dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/budgets/<budget_id>', methods=['PUT'])
def update_budget(budget_id):
    data = request.get_json()
    
    try:
        # Verificar se o orçamento pertence ao usuário
        budget = current_app.db.get_budget_by_id(budget_id)
        if not budget or budget.user_id != request.user_id:
            return jsonify({"error": "Budget not found"}), 404
        
        # Atualizar orçamento
        success = current_app.db.update_budget(budget_id, **data)
        if not success:
            return jsonify({"error": "Failed to update budget"}), 500
        
        updated_budget = current_app.db.get_budget_by_id(budget_id)
        return jsonify(updated_budget.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/budgets/<budget_id>', methods=['DELETE'])
def delete_budget(budget_id):
    try:
        # Verificar se o orçamento pertence ao usuário
        budget = current_app.db.get_budget_by_id(budget_id)
        if not budget or budget.user_id != request.user_id:
            return jsonify({"error": "Budget not found"}), 404
        
        # Excluir orçamento
        success = current_app.db.delete_budget(budget_id)
        if not success:
            return jsonify({"error": "Failed to delete budget"}), 500
            
        return jsonify({"message": "Budget deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/budgets/alerts', methods=['GET'])
def get_budget_alerts():
    month = request.args.get('month', type=int, default=datetime.now().month)
    year = request.args.get('year', type=int, default=datetime.now().year)
    
    alerts = current_app.db.check_budget_alerts(request.user_id, month, year)
    return jsonify(alerts), 200

# Rotas de notificações
@api_bp.route('/notifications', methods=['GET'])
def get_notifications():
    notifications = current_app.db.get_notifications(request.user_id)
    return jsonify([n.dict() for n in notifications]), 200

@api_bp.route('/notifications/unread', methods=['GET'])
def get_unread_notifications():
    notifications = current_app.db.get_unread_notifications(request.user_id)
    return jsonify([n.dict() for n in notifications]), 200

@api_bp.route('/notifications/<notification_id>/read', methods=['PUT'])
def mark_notification_as_read(notification_id):
    try:
        success = current_app.db.mark_notification_as_read(notification_id)
        if not success:
            return jsonify({"error": "Failed to mark notification as read"}), 500
        
        return jsonify({"message": "Notification marked as read"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Rotas de assinatura
@api_bp.route('/subscription', methods=['GET'])
def get_subscription():
    subscription = current_app.db.get_user_subscription(request.user_id)
    if not subscription:
        return jsonify({"plan": "free"}), 200
    
    return jsonify(subscription), 200

@api_bp.route('/subscription', methods=['POST'])
def create_subscription():
    data = request.get_json()
    plan = data.get('plan')
    payment_method = data.get('payment_method')
    
    if not plan or not payment_method:
        return jsonify({"error": "Plan and payment method are required"}), 400
    
    try:
        user = current_app.db.get_user_by_id(request.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        result = PaymentService(current_app.db).create_subscription(
            request.user_id, user.email, user.name, plan, payment_method
        )
        
        if "error" in result:
            return jsonify({"error": result["error"]}), 400
        
        return jsonify(result), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/subscription/cancel', methods=['POST'])
def cancel_subscription():
    try:
        subscription = current_app.db.get_user_subscription(request.user_id)
        if not subscription or subscription["status"] != SubscriptionStatus.ACTIVE.value:
            return jsonify({"error": "No active subscription found"}), 404
        
        success = PaymentService(current_app.db).cancel_subscription(subscription["stripe_subscription_id"])
        if not success:
            return jsonify({"error": "Failed to cancel subscription"}), 500
        
        return jsonify({"message": "Subscription canceled"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Rotas de dashboard
@api_bp.route('/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    month = request.args.get('month', type=int, default=datetime.now().month)
    year = request.args.get('year', type=int, default=datetime.now().year)
    
    try:
        # Calcular totais
        total_income = current_app.db.get_total_by_type(request.user_id, TransactionType.INCOME.value, month, year)
        total_expenses = current_app.db.get_total_by_type(request.user_id, TransactionType.EXPENSE.value, month, year)
        balance = total_income - total_expenses
        
        # Resumo por categoria
        category_summary = current_app.db.get_category_summary(
            request.user_id, TransactionType.EXPENSE.value, month, year
        )
        
        # Progresso das metas
        goals = current_app.db.get_goals(request.user_id)
        goals_progress = [
            {
                "id": g.id,
                "name": g.name,
                "progress": (g.current_amount / g.target_amount) * 100 if g.target_amount > 0 else 0,
                "target_date": g.target_date.isoformat() if isinstance(g.target_date, date) else g.target_date
            }
            for g in goals
        ]
        
        # Dados para gráficos
        income_data = []
        expenses_data = []
        months = []
        
        # Obter dados dos últimos 6 meses
        for i in range(5, -1, -1):
            target_month = month - i
            target_year = year
            if target_month <= 0:
                target_month += 12
                target_year -= 1
                
            months.append(f"{calendar.month_abbr[target_month]}/{target_year}")
            income_data.append(current_app.db.get_total_by_type(request.user_id, TransactionType.INCOME.value, target_month, target_year))
            expenses_data.append(current_app.db.get_total_by_type(request.user_id, TransactionType.EXPENSE.value, target_month, target_year))
        
        return jsonify({
            "balance": balance,
            "income": total_income,
            "expenses": total_expenses,
            "category_summary": category_summary,
            "goals_progress": goals_progress,
            "income_data": income_data,
            "expenses_data": expenses_data,
            "months": months
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Rotas de exportação
@api_bp.route('/export/transactions/csv', methods=['GET'])
def export_transactions_csv():
    month = request.args.get('month', type=int, default=datetime.now().month)
    year = request.args.get('year', type=int, default=datetime.now().year)
    
    try:
        transactions = current_app.db.get_transactions(request.user_id, month, year)
        
        # Criar CSV em memória
        output = BytesIO()
        writer = csv.writer(output)
        
        # Cabeçalho
        writer.writerow(["ID", "Data", "Tipo", "Categoria", "Valor", "Descrição", "Recorrente"])
        
        # Dados
        for t in transactions:
            writer.writerow([
                t.id,
                t.date.isoformat() if isinstance(t.date, date) else t.date,
                "Receita" if t.type == TransactionType.INCOME.value else "Despesa",
                t.category,
                t.amount,
                t.description or "",
                "Sim" if t.recurring else "Não"
            ])
        
        output.seek(0)
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'transactions-{month}-{year}.csv'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Rotas de usuário
@api_bp.route('/user', methods=['GET'])
def get_user():
    try:
        user = current_app.db.get_user_by_id(request.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify(user.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/user', methods=['PUT'])
def update_user():
    data = request.get_json()
    
    try:
        # Campos permitidos para atualização
        allowed_fields = ['name', 'currency', 'risk_profile', 'notification_pref']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({"error": "No valid fields to update"}), 400
            
        success = current_app.db.update_user(request.user_id, **update_data)
        if not success:
            return jsonify({"error": "Failed to update user"}), 500
        
        updated_user = current_app.db.get_user_by_id(request.user_id)
        return jsonify(updated_user.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500