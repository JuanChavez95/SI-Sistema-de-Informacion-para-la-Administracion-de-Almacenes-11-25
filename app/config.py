import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# ✅ Cargar variables del archivo .env
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'mi-clave-super-secreta-123456')
    
    # Credenciales de MySQL
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'grand batle124')
    MYSQL_DB = os.getenv('MYSQL_DB', 'sistema_administracion_almacenes_3')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))