import sys
from os.path import dirname, abspath
sys.path.insert(0, dirname(dirname(abspath(__file__))))
from flask import Flask, render_template
from config import Config
from app.auth import auth_bp
from app.routes import api_bp
from app.payments import PaymentService
from app.database import Database
from app import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
