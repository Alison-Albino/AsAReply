import os
import time
import logging
import threading
import base64
import asyncio
from datetime import datetime
from app import app, db
from models import WhatsAppConnection, Conversation, Message, AutoResponse
from ai_service import generate_ai_response, analyze_message_intent
from evolution_api_service import evolution_service

class WhatsAppService:
    """Service for managing WhatsApp integration"""
    
    def __init__(self):
        self.is_connected = False
        self.typing_threads = {}  # Track typing threads by conversation
        
    def generate_qr_code(self):
        """Generate QR code usando Evolution API"""
        try:
            # Primeiro, criar/verificar instância
            instance_result = evolution_service.create_instance()
            if not instance_result.get('success'):
                logging.warning("Tentando obter QR de instância existente...")
            
            # Obter QR Code
            qr_result = evolution_service.get_qr_code()
            
            if qr_result.get('success'):
                qr_code = qr_result.get('qr_code', '')
                qr_base64 = qr_result.get('qr_base64', '')
                
                with app.app_context():
                    connection = WhatsAppConnection.query.first()
                    if not connection:
                        connection = WhatsAppConnection()
                        db.session.add(connection)
                    
                    connection.qr_code = qr_base64 or qr_code
                    connection.is_connected = False
                    db.session.commit()
                
                logging.info("QR Code obtido da Evolution API")
                return qr_base64 or qr_code
            else:
                logging.error(f"Erro ao obter QR Code: {qr_result.get('error')}")
                return None
                
        except Exception as e:
            logging.error(f"Erro ao gerar QR Code: {e}")
            return None
    
    def simulate_connection(self):
        """Simulate WhatsApp connection - removed auto-connection"""
        # Conexão automática removida - agora só conecta quando receber confirmação real
        logging.info("QR Code gerado - aguardando escaneamento real")
    
    def start_typing_simulation(self, phone_number: str):
        """Start typing simulation for a conversation"""
        def typing_worker():
            # Simulate typing for 2-5 seconds
            typing_duration = 3
            logging.info(f"Typing simulation started for {phone_number}")
            time.sleep(typing_duration)
            logging.info(f"Typing simulation ended for {phone_number}")
        
        # Cancel existing typing thread if any
        if phone_number in self.typing_threads:
            self.typing_threads[phone_number] = None
        
        # Start new typing thread
        thread = threading.Thread(target=typing_worker)
        self.typing_threads[phone_number] = thread
        thread.start()
    
    def stop_typing_simulation(self, phone_number: str):
        """Stop typing simulation when new message received"""
        if phone_number in self.typing_threads:
            self.typing_threads[phone_number] = None
            logging.info(f"Typing simulation interrupted for {phone_number}")
    
    def process_incoming_message(self, phone_number: str, message_content: str, contact_name: str = ""):
        """Process incoming WhatsApp message"""
        with app.app_context():
            # Stop any ongoing typing simulation
            self.stop_typing_simulation(phone_number)
            
            # Find or create conversation
            conversation = Conversation.query.filter_by(phone_number=phone_number).first()
            if not conversation:
                conversation = Conversation()
                conversation.phone_number = phone_number
                conversation.contact_name = contact_name or phone_number
                db.session.add(conversation)
                db.session.commit()
            
            # Save incoming message
            incoming_message = Message()
            incoming_message.conversation_id = conversation.id
            incoming_message.content = message_content
            incoming_message.is_from_user = True
            incoming_message.message_type = 'text'
            db.session.add(incoming_message)
            db.session.commit()
            
            # Start typing simulation
            self.start_typing_simulation(phone_number)
            
            # Generate response
            response_text = self.generate_response(message_content, conversation)
            
            # Save and send response
            self.send_response(conversation, response_text)
    
    def generate_response(self, message_content: str, conversation: Conversation) -> str:
        """Generate appropriate response for the message"""
        # Check for standard auto-responses first
        auto_response = AutoResponse.query.filter(
            AutoResponse.is_active == True,
            AutoResponse.trigger_keyword.ilike(f'%{message_content.lower()}%')
        ).first()
        
        if auto_response:
            return auto_response.response_text
        
        # Analyze message intent
        intent = analyze_message_intent(message_content)
        
        # If urgent or requires human, provide fallback response
        if intent.get('urgencia') == 'alto' or intent.get('requer_humano'):
            return ("Obrigado pela sua mensagem. Detectei que pode ser algo urgente. "
                   "Nossa equipe será notificada e retornará o contato em breve.")
        
        # Generate AI response
        recent_messages = Message.query.filter_by(
            conversation_id=conversation.id
        ).order_by(Message.timestamp.desc()).limit(10).all()
        
        return generate_ai_response(message_content, recent_messages[::-1])
    
    def send_response(self, conversation: Conversation, response_text: str):
        """Send response message usando Evolution API"""
        try:
            # Simular digitação antes de enviar
            evolution_service.set_typing(conversation.phone_number, True)
            
            # Aguardar um pouco para simular digitação
            time.sleep(2)
            
            # Enviar mensagem via Evolution API
            send_result = evolution_service.send_message(conversation.phone_number, response_text)
            
            # Parar digitação
            evolution_service.set_typing(conversation.phone_number, False)
            
            if send_result.get('success'):
                # Salvar no banco apenas se envio foi bem-sucedido
                response_message = Message()
                response_message.conversation_id = conversation.id
                response_message.content = response_text
                response_message.is_from_user = False
                response_message.message_type = 'text'
                response_message.response_type = 'ai'
                
                db.session.add(response_message)
                conversation.updated_at = datetime.utcnow()
                db.session.commit()
                
                logging.info(f"Mensagem enviada via Evolution API para {conversation.phone_number}")
            else:
                logging.error(f"Erro ao enviar via Evolution API: {send_result.get('error')}")
                
        except Exception as e:
            logging.error(f"Erro ao enviar resposta: {e}")
    
    def get_connection_status(self):
        """Get current connection status da Evolution API"""
        with app.app_context():
            connection = WhatsAppConnection.query.first()
            if not connection:
                connection = WhatsAppConnection()
                db.session.add(connection)
                db.session.commit()
            
            # Tentar verificar status na Evolution API (sem logs de erro se não estiver configurada)
            try:
                api_status = evolution_service.get_connection_state()
                
                if api_status.get('success'):
                    api_data = api_status.get('data', {})
                    state = api_data.get('state', 'close')
                    
                    # Atualizar status no banco
                    connection.is_connected = state == 'open'
                    if state == 'open':
                        connection.last_connected = datetime.utcnow()
                        connection.qr_code = None
                    
                    db.session.commit()
                    
                    return {
                        'is_connected': connection.is_connected,
                        'qr_code': connection.qr_code,
                        'last_connected': connection.last_connected,
                        'api_state': state,
                        'evolution_api_available': True
                    }
                else:
                    return {
                        'is_connected': connection.is_connected,
                        'qr_code': connection.qr_code,
                        'last_connected': connection.last_connected,
                        'api_state': 'disconnected',
                        'evolution_api_available': False,
                        'evolution_error': api_status.get('error', 'API não disponível')
                    }
                    
            except Exception:
                # Fallback para status local se Evolution API não estiver disponível
                return {
                    'is_connected': connection.is_connected,
                    'qr_code': connection.qr_code,
                    'last_connected': connection.last_connected,
                    'api_state': 'not_configured',
                    'evolution_api_available': False
                }

# Global service instance
whatsapp_service = WhatsAppService()

def simulate_incoming_messages():
    """Simulate incoming messages for testing"""
    import random
    
    sample_messages = [
        ("5511999999999", "Olá", "João Silva"),
        ("5511888888888", "Preciso de ajuda", "Maria Santos"),
        ("5511777777777", "Qual o horário de funcionamento?", "Pedro Costa"),
        ("5511666666666", "Obrigado pelo atendimento", "Ana Lima"),
    ]
    
    def send_test_message():
        time.sleep(random.randint(10, 30))
        phone, message, name = random.choice(sample_messages)
        whatsapp_service.process_incoming_message(phone, message, name)
        logging.info(f"Test message sent: {message}")
    
    # Start background thread for test messages
    threading.Thread(target=send_test_message, daemon=True).start()
