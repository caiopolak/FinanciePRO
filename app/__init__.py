import logging
from flask import Flask
from config import Config
from .database import Database
from .payments import PaymentService

db = Database()

def create_app():
    app = Flask(__name__, template_folder='templates')
    app.config.from_object(Config)
    
    # Configurar logger
    app.logger.setLevel(logging.INFO)
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
    app.db = db
    app.payment_service = PaymentService(db)
    
    # Rota principal
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app