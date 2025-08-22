from datetime import datetime
from app import db

class Conversation(db.Model):
    """Model for storing WhatsApp conversations"""
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False)
    contact_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    ai_paused = db.Column(db.Boolean, default=False)  # True when human takes over
    paused_at = db.Column(db.DateTime)  # When AI was paused
    
    # Relationship with messages
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan')

class Message(db.Model):
    """Model for storing individual messages"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_from_user = db.Column(db.Boolean, nullable=False)  # True if from user, False if from bot
    message_type = db.Column(db.String(20), default='text')  # text, image, audio, etc.
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    response_type = db.Column(db.String(20))  # 'standard', 'ai', or None for user messages

class AutoResponse(db.Model):
    """Model for storing automatic responses"""
    id = db.Column(db.Integer, primary_key=True)
    trigger_keyword = db.Column(db.String(100), nullable=False, unique=True)
    response_text = db.Column(db.Text, nullable=False)
    response_type = db.Column(db.String(20), default='simple')  # 'simple' or 'multiple'
    trigger_type = db.Column(db.String(20), default='first_message')  # 'first_message' or 'follow_up'
    main_question = db.Column(db.Text)  # Para respostas com múltipla escolha
    option_a = db.Column(db.String(200))  # Opção A
    option_b = db.Column(db.String(200))  # Opção B
    option_c = db.Column(db.String(200))  # Opção C
    option_d = db.Column(db.String(200))  # Opção D
    pause_ai = db.Column(db.Boolean, default=False)  # Pause AI after this response
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SystemSettings(db.Model):
    """Model for storing system settings"""
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(50), nullable=False, unique=True)
    setting_value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WhatsAppConnection(db.Model):
    """Model for storing WhatsApp connection status"""
    id = db.Column(db.Integer, primary_key=True)
    is_connected = db.Column(db.Boolean, default=False)
    qr_code = db.Column(db.Text)  # Base64 encoded QR code
    last_connected = db.Column(db.DateTime)
    session_data = db.Column(db.Text)  # Serialized session data
