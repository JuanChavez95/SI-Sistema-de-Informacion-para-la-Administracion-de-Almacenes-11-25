from flask import Flask
from app.config import Config

def create_app():
    app = Flask(__name__)
    
    # ✅ Configuración desde .env (a través de Config)
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    
    # Registrar blueprints
    from app.controllers import auth, dashboard
    from app.controllers import almacen
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(almacen.almacen_bp)
    
    print("✅ App Flask creada exitosamente")
    print(f"   Base de datos: {Config.MYSQL_DB}")
    print(f"   Host: {Config.MYSQL_HOST}")
    
    return app





