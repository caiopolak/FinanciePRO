import logging
from flask import Flask, render_template
from config import Config # type: ignore
from .database import Database
from .payments import PaymentService

db = Database()

def create_app():
    app = Flask(__name__, template_folder='templates')
    app.config.from_object(Config)
    
    # Configurar logger detalhado
    app.logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
    ))
    app.logger.addHandler(handler)

    # Registrar blueprints
    from .auth import auth_bp
    from .routes import api_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Inicializar serviços
    try:
        app.db = Database()
        app.logger.info("Database connection established")
    except Exception as e:
        app.logger.error(f"Database connection failed: {str(e)}")
        raise e
    
    app.payment_service = PaymentService(app.db)
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app