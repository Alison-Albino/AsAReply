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
        # Check if ai_paused column exists in conversation table
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
        
        # Check if new columns exist in auto_response table
        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(auto_response)"))
            columns = [row[1] for row in result]
            
            if 'trigger_type' not in columns:
                conn.execute(text("ALTER TABLE auto_response ADD COLUMN trigger_type VARCHAR(20) DEFAULT 'first_message'"))
                conn.commit()
                logging.info("✅ Added trigger_type column")
            
            if 'main_question' not in columns:
                conn.execute(text("ALTER TABLE auto_response ADD COLUMN main_question TEXT"))
                conn.commit()
                logging.info("✅ Added main_question column")
                
            if 'option_a' not in columns:
                conn.execute(text("ALTER TABLE auto_response ADD COLUMN option_a VARCHAR(200)"))
                conn.commit()
                logging.info("✅ Added option_a column")
                
            if 'option_b' not in columns:
                conn.execute(text("ALTER TABLE auto_response ADD COLUMN option_b VARCHAR(200)"))
                conn.commit()
                logging.info("✅ Added option_b column")
                
            if 'option_c' not in columns:
                conn.execute(text("ALTER TABLE auto_response ADD COLUMN option_c VARCHAR(200)"))
                conn.commit()
                logging.info("✅ Added option_c column")
                
            if 'option_d' not in columns:
                conn.execute(text("ALTER TABLE auto_response ADD COLUMN option_d VARCHAR(200)"))
                conn.commit()
                logging.info("✅ Added option_d column")
            
    except Exception as e:
        logging.info(f"Migration info: {e}")
    
    logging.info("Database tables created successfully")
