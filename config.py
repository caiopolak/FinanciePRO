import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Configurações do Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rnpkqnrxpwxmnzaqthqm.supabase.co")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJucGtxbnJ4cHd4bW56YXF0aHFtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk1OTE1NzgsImV4cCI6MjA2NTE2NzU3OH0.FD3r_Gn3HnO1TJHGKpbc6uBix3--bdAdcwPn6gRqkL0")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJucGtxbnJ4cHd4bW56YXF0aHFtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk1OTE1NzgsImV4cCI6MjA2NTE2NzU3OH0.FD3r_Gn3HnO1TJHGKpbc6uBix3--bdAdcwPn6gRqkL0"))
    
    # Configurações do Stripe
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_51RY7UHRr2akl2mosjxX3BQI7c9P3TuhHvtipmsBWr74iuz4c4cuacmo6IdjE7ZtTylHBmHOm7ozx7k6YKnVBpKcO00uzEii57b")
    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY", "pk_test_51RY7UHRr2akl2mos7YrUds6SUxyD163Z1xnrpfemYMA9a3KnkIJirISac1wCEHiHGSu3KS6qszJmy6ERD08MRFuW00GiBi06sm")
    
    # Configurações do aplicativo
    SECRET_KEY = os.getenv("SECRET_KEY", "ZSMHZnSutbGr+cBEqyIgWhgmmAZBD3E+lppzTQjueeFa3ZPYW5H+B5L2iwbjzQDM3Qk2QjDWJFNe9rNNwk1taQ==")
    
    # Adicione esta linha para resolver o erro de JWT
    JWT_SECRET_KEY = os.getenv("SECRET_KEY", "ZSMHZnSutbGr+cBEqyIgWhgmmAZBD3E+lppzTQjueeFa3ZPYW5H+B5L2iwbjzQDM3Qk2QjDWJFNe9rNNwk1taQ==")
    JWT_ALGORITHM = "HS256"

    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configurações de e-mail (opcional)
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")
    
    # Cores da identidade visual
    COLOR_PRIMARY = "#003f5c"     # Azul petróleo
    COLOR_SECONDARY = "#2f9e44"   # Verde esmeralda
    COLOR_LIGHT = "#f4f4f4"       # Cinza gelo
    COLOR_DARK = "#2b2b2b"        # Cinza grafite
    COLOR_WARNING = "#f8961e"     # Laranja vivo
    COLOR_DANGER = "#d62828"      # Vermelho claro