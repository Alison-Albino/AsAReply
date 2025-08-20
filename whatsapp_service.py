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
from baileys_service import baileys_service

class WhatsAppService:
    """Service for managing WhatsApp integration"""
    
    def __init__(self):
        self.is_connected = False
        self.typing_threads = {}  # Track typing threads by conversation
        self.message_queues = {}  # Queue of messages per user
        self.queue_timers = {}    # Timers for processing queues
        self.QUEUE_WAIT_TIME = 8   # Seconds to wait for additional messages
        
    def generate_qr_code(self):
        """Generate QR code usando Baileys local"""
        try:
            logging.info("📱 Gerando QR Code...")
            
            # Aguardar um pouco para o serviço estar pronto
            time.sleep(2)
            
            # Obter QR Code do serviço Baileys
            qr_result = baileys_service.get_qr_code()
            
            if qr_result.get('success'):
                qr_code = qr_result.get('qr_code', '')
                qr_base64 = qr_result.get('qr_image', '')
                
                with app.app_context():
                    connection = WhatsAppConnection.query.first()
                    if not connection:
                        connection = WhatsAppConnection()
                        db.session.add(connection)
                    
                    connection.qr_code = qr_base64 or qr_code
                    connection.is_connected = False
                    db.session.commit()
                
                logging.info("✅ QR Code gerado com sucesso!")
                return qr_base64 or qr_code
            else:
                logging.warning(f"QR Code ainda não está pronto: {qr_result.get('message', 'Aguardando...')}")
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
    
    def add_message_to_queue(self, phone_number: str, message_content: str, conversation: Conversation):
        """Add message to queue and manage timer"""
        # Initialize queue if not exists
        if phone_number not in self.message_queues:
            self.message_queues[phone_number] = []
        
        # Add message to queue (save only conversation ID to avoid session issues)
        self.message_queues[phone_number].append({
            'content': message_content,
            'timestamp': datetime.utcnow(),
            'conversation_id': conversation.id
        })
        
        logging.info(f"📥 Mensagem adicionada à fila para {phone_number}. Total na fila: {len(self.message_queues[phone_number])}")
        
        # Cancel existing timer if any
        if phone_number in self.queue_timers:
            self.queue_timers[phone_number].cancel()
        
        # Start typing simulation
        self.start_typing_simulation(phone_number)
        
        # Create new timer
        timer = threading.Timer(self.QUEUE_WAIT_TIME, self.process_message_queue, [phone_number])
        self.queue_timers[phone_number] = timer
        timer.start()
        
        logging.info(f"⏱️ Timer iniciado para {phone_number} ({self.QUEUE_WAIT_TIME}s)")
    
    def process_message_queue(self, phone_number: str):
        """Process all queued messages for a user"""
        if phone_number not in self.message_queues or not self.message_queues[phone_number]:
            return
        
        with app.app_context():
            try:
                messages = self.message_queues[phone_number].copy()
                conversation_id = messages[0]['conversation_id']
                
                # Clear the queue
                self.message_queues[phone_number] = []
                if phone_number in self.queue_timers:
                    del self.queue_timers[phone_number]
                
                # Get fresh conversation object from database in this session
                conversation = Conversation.query.get(conversation_id)
                if not conversation:
                    logging.error(f"Conversa não encontrada: {conversation_id}")
                    return
                
                logging.info(f"🔄 Processando fila de {len(messages)} mensagens para {phone_number}")
                
                # Combine all messages into context
                combined_messages = []
                for msg in messages:
                    combined_messages.append(msg['content'])
                
                # Generate single response for all messages
                response_text = self.generate_response_for_queue(combined_messages, conversation)
                
                # Send response
                self.send_response(conversation, response_text)
                
            except Exception as e:
                logging.error(f"Erro ao processar fila de mensagens: {e}")
                # Try to get conversation for fallback
                try:
                    conversation = Conversation.query.filter_by(phone_number=phone_number).first()
                    if conversation:
                        self.send_response(conversation, "Desculpe, estou com alguns problemas técnicos. Tente novamente!")
                except:
                    logging.error(f"Não foi possível enviar mensagem de fallback para {phone_number}")
    
    def process_incoming_message(self, phone_number: str, message_content: str, contact_name: str = ""):
        """Process incoming WhatsApp message with queue system"""
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
            
            # Add message to queue
            self.add_message_to_queue(phone_number, message_content, conversation)
    
    def generate_response(self, message_content: str, conversation: Conversation) -> str:
        """Generate AI response using custom prompt for single message"""
        try:
            # Get recent conversation history for context
            recent_messages = Message.query.filter_by(
                conversation_id=conversation.id
            ).order_by(Message.timestamp.desc()).limit(10).all()
            
            # Generate AI response using custom prompt
            return generate_ai_response(message_content, recent_messages[::-1])
            
        except Exception as e:
            logging.error(f"Erro ao gerar resposta: {e}")
            return "Olá! Estou passando por alguns ajustes técnicos. Que tal tentar novamente em alguns minutos?"
    
    def generate_response_for_queue(self, messages_list: list, conversation: Conversation) -> str:
        """Generate AI response for multiple queued messages"""
        try:
            # Get recent conversation history for context
            recent_messages = Message.query.filter_by(
                conversation_id=conversation.id
            ).order_by(Message.timestamp.desc()).limit(10).all()
            
            # Combine all queued messages into a single context
            if len(messages_list) == 1:
                combined_message = messages_list[0]
            else:
                combined_message = f"O usuário enviou {len(messages_list)} mensagens seguidas:\n\n"
                for i, msg in enumerate(messages_list, 1):
                    combined_message += f"Mensagem {i}: {msg}\n"
                combined_message += f"\nPor favor, responda considerando todas essas {len(messages_list)} mensagens de forma integrada."
            
            logging.info(f"🤖 Gerando resposta IA para {len(messages_list)} mensagens combinadas")
            
            # Generate AI response using custom prompt
            return generate_ai_response(combined_message, recent_messages[::-1])
            
        except Exception as e:
            logging.error(f"Erro ao gerar resposta para fila: {e}")
            return "Olá! Vi que você enviou algumas mensagens. Estou com problemas técnicos no momento, mas vou retornar assim que possível!"
    
    def send_response(self, conversation: Conversation, response_text: str):
        """Send response message usando Baileys"""
        try:
            # Simular digitação antes de enviar
            baileys_service.set_typing(conversation.phone_number, True)
            
            # Aguardar um pouco para simular digitação
            time.sleep(2)
            
            # Enviar mensagem via Baileys
            send_result = baileys_service.send_message(conversation.phone_number, response_text)
            
            # Parar digitação
            baileys_service.set_typing(conversation.phone_number, False)
            
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
                
                logging.info(f"📤 Mensagem enviada via Baileys para {conversation.phone_number}")
            else:
                logging.error(f"❌ Erro ao enviar via Baileys: {send_result.get('error')}")
                
        except Exception as e:
            logging.error(f"Erro ao enviar resposta: {e}")
    
    def get_connection_status(self):
        """Get current connection status do Baileys"""
        with app.app_context():
            connection = WhatsAppConnection.query.first()
            if not connection:
                connection = WhatsAppConnection()
                db.session.add(connection)
                db.session.commit()
            
            # Verificar status no serviço Baileys
            try:
                baileys_status = baileys_service.get_connection_status()
                
                if baileys_status.get('success') != False:
                    # Atualizar status no banco baseado no Baileys
                    is_connected = baileys_status.get('connected', False)
                    
                    connection.is_connected = is_connected
                    if is_connected:
                        connection.last_connected = datetime.utcnow()
                        connection.qr_code = None
                    
                    db.session.commit()
                    
                    return {
                        'is_connected': connection.is_connected,
                        'qr_code': connection.qr_code,
                        'last_connected': connection.last_connected,
                        'baileys_status': baileys_status.get('status', 'unknown'),
                        'qr_available': baileys_status.get('qr_available', False),
                        'user_info': baileys_status.get('user'),
                        'service_running': True
                    }
                else:
                    return {
                        'is_connected': False,
                        'qr_code': connection.qr_code,
                        'last_connected': connection.last_connected,
                        'baileys_status': 'service_error',
                        'service_running': False,
                        'error': baileys_status.get('error', 'Serviço não está rodando')
                    }
                    
            except Exception as e:
                # Fallback para status local
                return {
                    'is_connected': connection.is_connected,
                    'qr_code': connection.qr_code,
                    'last_connected': connection.last_connected,
                    'baileys_status': 'error',
                    'service_running': False,
                    'error': str(e)
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
