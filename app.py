import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "asa-secret-key-2024")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///asa_whatsapp.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models to create tables
    import models  # noqa: F401
    db.create_all()
    
    # Add new columns if they don't exist (migration)
    try:
        from sqlalchemy import text
        # Check if ai_paused column exists
        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(conversation)"))
            columns = [row[1] for row in result]
            
            if 'ai_paused' not in columns:
                conn.execute(text("ALTER TABLE conversation ADD COLUMN ai_paused BOOLEAN DEFAULT 0"))
                conn.commit()
                logging.info("✅ Added ai_paused column")
                
            if 'paused_at' not in columns:
                conn.execute(text("ALTER TABLE conversation ADD COLUMN paused_at DATETIME"))
                conn.commit()
                logging.info("✅ Added paused_at column")
            
    except Exception as e:
        logging.info(f"Migration info: {e}")
    
    logging.info("Database tables created successfully")
