from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import jwt
import os
from typing import Optional, Dict
from .models import User, UserPlan

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    
    data = request.get_json() if request.is_json else request.form
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    
    if not email or not password or not name:
        return jsonify({"error": "Email, password and name are required"}), 400
    
    # Verificar se o usuário já existe
    existing_user = current_app.db.get_user_by_email(email)
    if existing_user:
        return jsonify({"error": "User already exists"}), 400
    
    # Criar novo usuário
    try:
        user = current_app.db.create_user(email, password, name)
        if not user:
            return jsonify({"error": "Failed to create user"}), 500
        
        # Gerar token JWT
        token = generate_jwt_token(user.id)
        
        return jsonify({
            "message": "User registered successfully",
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "plan": user.plan
            }
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        # Verificar se já está autenticado
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            payload = verify_jwt_token(token)
            if payload:
                return jsonify({"message": "Already authenticated"}), 200
        
        return render_template('login.html')
    
    data = request.get_json() if request.is_json else request.form
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    try:
        # Autenticar com Supabase Auth
        response = current_app.db.client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        # Obter dados do usuário diretamente da resposta
        user_data = response.user.user_metadata
        user = User(
            id=response.user.id,
            email=email,
            name=user_data.get("name", ""),
            plan=user_data.get("plan", UserPlan.FREE.value)
        )    

        if not response.user:
            return jsonify({"error": "Invalid credentials"}), 401
        
        # Obter dados do usuário
        user = current_app.db.get_user_by_id(response.user.id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Gerar token JWT
        token = generate_jwt_token(user.id)
        
        # Armazenar na sessão
        session['user_id'] = user.id
        session['token'] = token
        
        return jsonify({
            "message": "Login successful",
            "token": token,
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
    return jsonify({"message": "Logged out successfully"}), 200

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password.html')
    
    email = request.get_json().get('email') if request.is_json else request.form.get('email')
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
    
    try:
        current_app.db.client.auth.reset_password_email(email)
        return jsonify({"message": "Password reset email sent"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'GET':
        token = request.args.get('token')
        return render_template('reset_password.html', token=token)
    
    data = request.get_json() if request.is_json else request.form
    token = data.get('token')
    new_password = data.get('new_password')
    
    if not token or not new_password:
        return jsonify({"error": "Token and new password are required"}), 400
    
    try:
        current_app.db.client.auth.update_user({
            "password": new_password
        })
        
        return jsonify({"message": "Password updated successfully"}), 200
    except Exception as e:
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
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None