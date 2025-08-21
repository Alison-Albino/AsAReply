#!/usr/bin/env python3
"""
Migration script to add new columns to AutoResponse table
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import AutoResponse
from sqlalchemy import text

def migrate_database():
    """Add new columns to AutoResponse table"""
    with app.app_context():
        print("🔄 Iniciando migração do banco de dados...")
        
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('auto_responses')]
            
            # Add response_type column if it doesn't exist
            if 'response_type' not in columns:
                print("  ➕ Adicionando coluna 'response_type'...")
                db.session.execute(text("ALTER TABLE auto_responses ADD COLUMN response_type VARCHAR(20) DEFAULT 'simple'"))
                db.session.commit()
                print("  ✅ Coluna 'response_type' adicionada com sucesso")
            else:
                print("  ℹ️  Coluna 'response_type' já existe")
            
            # Add pause_ai column if it doesn't exist
            if 'pause_ai' not in columns:
                print("  ➕ Adicionando coluna 'pause_ai'...")
                db.session.execute(text("ALTER TABLE auto_responses ADD COLUMN pause_ai BOOLEAN DEFAULT FALSE"))
                db.session.commit()
                print("  ✅ Coluna 'pause_ai' adicionada com sucesso")
            else:
                print("  ℹ️  Coluna 'pause_ai' já existe")
            
            print("✅ Migração concluída com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro na migração: {e}")
            db.session.rollback()
            return False
            
        return True

if __name__ == '__main__':
    success = migrate_database()
    sys.exit(0 if success else 1)