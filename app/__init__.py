from flask import Flask
from app.config import Config

def create_app():
    app = Flask(__name__)
    
    # ✅ Configuración desde .env (a través de Config)
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    
    # Registrar blueprints
    from app.controllers import auth, dashboard
    from app.controllers import almacen
    from app.controllers import usuarios
    from app.controllers import empresas
    from app.controllers import recepciones
    from app.controllers import movimientos
    from app.controllers import inventarios
    from app.controllers import despachos
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(almacen.almacen_bp)
    app.register_blueprint(usuarios.usuarios_bp)
    app.register_blueprint(empresas.empresas_bp)
    app.register_blueprint(recepciones.recepciones_bp)
    app.register_blueprint(movimientos.movimientos_bp)
    app.register_blueprint(inventarios.inventarios_bp)
    app.register_blueprint(despachos.despachos_bp)
    
    print("✅ App Flask creada exitosamente")
    print(f"   Base de datos: {Config.MYSQL_DB}")
    print(f"   Host: {Config.MYSQL_HOST}")
    
    return app





