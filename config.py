import os

class Config:
    """Configuration settings for Bus Reservation and Fleet Scheduling System."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dbms-project-secret-key-2026-woxsen')
    
    # MySQL Database Connection parameters
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'Piduru@2006')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'bus_fleet_db')
    
    # Flask settings
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1')
