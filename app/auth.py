from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import jwt
import time
from typing import Optional, Dict
from .models import UserPlan

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    
    if not email or not password or not name:
        return jsonify({"error": "Email, senha e nome são obrigatórios"}), 400
    
    try:
        # Criar usuário no Supabase Auth
        auth_response = current_app.db.client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "name": name
                }
            }
        })
        
        if not auth_response.user:
            return jsonify({"error": "Falha ao criar usuário"}), 500
        
        # Esperar a criação do usuário
        time.sleep(2)
        
        # Criar registro na tabela users
        user_data = {
            "id": str(auth_response.user.id),
            "email": email,
            "name": name,
            "plan": UserPlan.FREE.value,
            "created_at": datetime.utcnow().isoformat()
        }
        
        response = current_app.db.client.table("users").insert(user_data).execute()
        
        if not response.data:
            # Tentar novamente se falhar
            time.sleep(1)
            response = current_app.db.client.table("users").insert(user_data).execute()
            if not response.data:
                return jsonify({"error": "Falha ao criar registro do usuário"}), 500
        
        user = User(**response.data[0])
        
        # Gerar token JWT
        token = generate_jwt_token(auth_response.user.id)
        
        return jsonify({
            "message": "Usuário registrado com sucesso",
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "plan": user.plan
            }
        }), 201
    except Exception as e:
        current_app.logger.error(f"Erro no registro: {str(e)}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email e senha são obrigatórios"}), 400
    
    try:
        # Autenticar com Supabase Auth
        auth_response = current_app.db.client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if not auth_response.user:
            return jsonify({"error": "Credenciais inválidas"}), 401
        
        # Obter dados do usuário
        user = current_app.db.get_user_by_id(auth_response.user.id)
        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404
        
        # Gerar token JWT
        token = generate_jwt_token(auth_response.user.id)
        
        return jsonify({
            "message": "Login realizado com sucesso",
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "plan": user.plan
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"Erro no login: {str(e)}")
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    email = request.get_json().get('email')
    
    if not email:
        return jsonify({"error": "Email é necessário"}), 400
    
    try:
        current_app.db.client.auth.reset_password_email(email)
        return jsonify({"message": "Email de reset de senha enviado com sucesso!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')
    
    if not token or not new_password:
        return jsonify({"error": "Token e nova senha são obrigatórios"}), 400
    
    try:
        # Método correto para redefinição de senha
        response = current_app.db.client.auth.reset_password(
            token=token,
            password=new_password
        )
        
        return jsonify({"message": "Senha atualizada com sucesso"}), 200
    except Exception as e:
        print(f"Error resetting password: {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_jwt_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm="HS256")

def verify_jwt_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(
            token, 
            current_app.config['JWT_SECRET_KEY'],
            algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None