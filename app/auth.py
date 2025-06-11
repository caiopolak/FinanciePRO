from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import jwt
import os
from typing import Optional, Dict
from .models import User, UserPlan

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    
    if not email or not password or not name:
        return jsonify({"error": "Email, senha e nome são obrigatórios"}), 400
    
    # Verificar se o usuário já existe
    existing_user = current_app.db.get_user_by_email(email)
    if existing_user:
        return jsonify({"error": "Usuário já existe"}), 400
    
    # Criar novo usuário
    try:
        user = current_app.db.create_user(email, password, name)
        if not user:
            return jsonify({"error": "Falha ao criar usuário"}), 500
        
        # Gerar token JWT do Supabase
        auth_response = current_app.db.client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if not auth_response.user:
            return jsonify({"error": "Falha ao autenticar usuário"}), 500
            
        return jsonify({
            "message": "Usuário registrado com sucesso",
            "token": auth_response.session.access_token,
            "user": {
                "id": auth_response.user.id,
                "email": email,
                "name": name,
                "plan": UserPlan.FREE.value
            }
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        # GERAR TOKEN JWT DA APLICAÇÃO
        token = generate_jwt_token(auth_response.user.id)  # <--- Adicione esta linha
        
        if not auth_response.user:
            return jsonify({"error": "Credenciais inválidas"}), 401
        
        # Obter dados do usuário
        user = current_app.db.get_user_by_id(auth_response.user.id)
        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404
        
        return jsonify({
            "message": "Login realizado com sucesso",
            "token": token,  # <--- Usar token JWT gerado
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "plan": user.plan
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Deslogado com sucesso!"}), 200

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password.html')
    
    email = request.get_json().get('email') if request.is_json else request.form.get('email')
    
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
        # Usar o token para atualizar a senha
        response = current_app.db.client.auth.update_user({
            "password": new_password
        })
        
        if not response.user:
            return jsonify({"error": "Falha ao atualizar senha"}), 400
            
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
    
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm="HS256")

def verify_jwt_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(
            token, 
            current_app.config['JWT_SECRET_KEY'],  # <--- Usar chave correta
            algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None