import os
import logging
import threading
from datetime import datetime
from flask import render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import check_password_hash, generate_password_hash
from app import app, db
from models import Conversation, Message, AutoResponse, SystemSettings, WhatsAppConnection
from whatsapp_service import whatsapp_service, simulate_incoming_messages
from baileys_service import baileys_service

# Admin credentials (in production, use proper user management)
ADMIN_PASSWORD_HASH = generate_password_hash(os.environ.get("ADMIN_PASSWORD", "admin123"))

@app.route('/')
def index():
    """Main page showing WhatsApp connection status"""
    connection_status = whatsapp_service.get_connection_status()
    return render_template('index_simple.html', connection_status=connection_status)

@app.route('/generate_qr')
def generate_qr():
    """Generate new QR code for WhatsApp connection"""
    qr_result = whatsapp_service.generate_qr_code()
    
    if qr_result:
        # Get the QR image from database
        with app.app_context():
            connection = WhatsAppConnection.query.first()
            if connection and connection.qr_code:
                qr_image = connection.qr_code
                logging.info("QR Code gerado - aguardando escaneamento")
                return jsonify({
                    'success': True,
                    'qr_code': qr_result,
                    'qr_image': qr_image
                })
    
    logging.error("Erro ao gerar QR Code")
    return jsonify({'success': False, 'error': 'Erro desconhecido'}), 500

@app.route('/simulate_scan')
def simulate_scan():
    """Simular escaneamento do QR Code para teste"""
    with app.app_context():
        connection = WhatsAppConnection.query.first()
        if connection:
            connection.is_connected = True
            connection.last_connected = datetime.utcnow()
            connection.qr_code = None
            db.session.commit()
            
    # Iniciar simulação de mensagens após "conexão"
    simulate_incoming_messages()
    
    return jsonify({'status': 'connected'})

@app.route('/connection_status')
def connection_status():
    """Get current connection status"""
    status = whatsapp_service.get_connection_status()
    return jsonify(status)

@app.route('/whatsapp-apis')
def whatsapp_apis():
    """Página explicativa sobre APIs WhatsApp disponíveis"""
    return render_template('whatsapp_apis.html')

@app.route('/evolution-setup')
def evolution_setup():
    """Página de configuração da Evolution API"""
    return render_template('evolution_setup.html')

@app.route('/api/test-baileys')
def test_baileys():
    """Testar conexão com serviço Baileys"""
    try:
        status = baileys_service.get_connection_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/baileys-status')
def baileys_status():
    """Obter status do serviço Baileys"""
    try:
        status = baileys_service.get_connection_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/get-qr')
def get_qr_code():
    """Obter QR Code do Baileys para exibir na tela"""
    try:
        qr_result = baileys_service.get_qr_code()
        return jsonify(qr_result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/qr-updated', methods=['POST'])
def qr_updated():
    """Webhook para QR Code atualizado"""
    try:
        data = request.get_json()
        qr_code = data.get('qr_code')
        
        if qr_code:
            with app.app_context():
                connection = WhatsAppConnection.query.first()
                if not connection:
                    connection = WhatsAppConnection()
                    db.session.add(connection)
                
                connection.qr_code = qr_code
                connection.is_connected = False
                db.session.commit()
                
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/connected', methods=['POST'])
def whatsapp_connected():
    """Webhook para WhatsApp conectado"""
    try:
        data = request.get_json()
        
        with app.app_context():
            connection = WhatsAppConnection.query.first()
            if not connection:
                connection = WhatsAppConnection()
                db.session.add(connection)
            
            connection.is_connected = True
            connection.last_connected = datetime.utcnow()
            connection.qr_code = None
            db.session.commit()
            
        logging.info("✅ WhatsApp conectado via Baileys!")
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/disconnected', methods=['POST'])
def whatsapp_disconnected():
    """Webhook para WhatsApp desconectado"""
    try:
        with app.app_context():
            connection = WhatsAppConnection.query.first()
            if connection:
                connection.is_connected = False
                db.session.commit()
                
        logging.info("❌ WhatsApp desconectado")
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/message-received', methods=['POST'])
def message_received():
    """Webhook para mensagem recebida"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        message = data.get('message')
        contact_name = data.get('contact_name', '')
        
        if phone and message:
            logging.info(f"📨 Mensagem recebida de {phone}: {message}")
            whatsapp_service.process_incoming_message(phone, message, contact_name)
            
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f"Erro ao processar mensagem: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Senha incorreta', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

def admin_required(f):
    """Decorator to require admin login"""
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    # Get statistics
    total_conversations = Conversation.query.count()
    total_messages = Message.query.count()
    active_responses = AutoResponse.query.filter_by(is_active=True).count()
    
    recent_conversations = Conversation.query.order_by(
        Conversation.updated_at.desc()
    ).limit(5).all()
    
    stats = {
        'total_conversations': total_conversations,
        'total_messages': total_messages,
        'active_responses': active_responses,
        'recent_conversations': recent_conversations
    }
    
    return render_template('admin_dashboard.html', stats=stats)

@app.route('/admin/conversations')
@admin_required
def admin_conversations():
    """View all conversations"""
    page = request.args.get('page', 1, type=int)
    conversations = Conversation.query.order_by(
        Conversation.updated_at.desc()
    ).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('conversations.html', conversations=conversations)

@app.route('/admin/conversation/<int:conversation_id>')
@admin_required
def view_conversation(conversation_id):
    """View specific conversation details"""
    conversation = Conversation.query.get_or_404(conversation_id)
    messages = Message.query.filter_by(
        conversation_id=conversation_id
    ).order_by(Message.timestamp.asc()).all()
    
    return render_template('conversation_detail.html', 
                         conversation=conversation, messages=messages)

@app.route('/admin/conversation/<int:conversation_id>/delete', methods=['POST'])
@admin_required
def delete_conversation(conversation_id):
    """Delete a conversation"""
    conversation = Conversation.query.get_or_404(conversation_id)
    db.session.delete(conversation)
    db.session.commit()
    flash('Conversa excluída com sucesso', 'success')
    return redirect(url_for('admin_conversations'))

@app.route('/admin/responses')
@admin_required
def admin_responses():
    """Manage auto responses"""
    responses = AutoResponse.query.order_by(AutoResponse.created_at.desc()).all()
    return render_template('responses.html', responses=responses)

@app.route('/admin/responses/add', methods=['GET', 'POST'])
@admin_required
def add_response():
    """Add new auto response"""
    if request.method == 'POST':
        trigger_keyword = request.form.get('trigger_keyword')
        response_text = request.form.get('response_text')
        is_active = request.form.get('is_active') == 'on'
        
        response = AutoResponse()
        response.trigger_keyword = trigger_keyword
        response.response_text = response_text
        response.is_active = is_active
        
        try:
            db.session.add(response)
            db.session.commit()
            flash('Resposta automática adicionada com sucesso', 'success')
            return redirect(url_for('admin_responses'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao adicionar resposta: palavra-chave já existe', 'error')
    
    return render_template('add_response.html')

@app.route('/admin/responses/<int:response_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_response(response_id):
    """Edit auto response"""
    response = AutoResponse.query.get_or_404(response_id)
    
    if request.method == 'POST':
        response.trigger_keyword = request.form.get('trigger_keyword')
        response.response_text = request.form.get('response_text')
        response.is_active = request.form.get('is_active') == 'on'
        
        try:
            db.session.commit()
            flash('Resposta automática atualizada com sucesso', 'success')
            return redirect(url_for('admin_responses'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar resposta', 'error')
    
    return render_template('edit_response.html', response=response)

@app.route('/admin/responses/<int:response_id>/delete', methods=['POST'])
@admin_required
def delete_response(response_id):
    """Delete auto response"""
    response = AutoResponse.query.get_or_404(response_id)
    db.session.delete(response)
    db.session.commit()
    flash('Resposta automática excluída com sucesso', 'success')
    return redirect(url_for('admin_responses'))

@app.route('/api/simulate_message', methods=['POST'])
def simulate_message():
    """API endpoint to simulate incoming message (for testing)"""
    data = request.get_json()
    phone = data.get('phone', '5511999999999')
    message = data.get('message', 'Teste')
    name = data.get('name', 'Usuário Teste')
    
    whatsapp_service.process_incoming_message(phone, message, name)
    
    return jsonify({'status': 'success'})

@app.context_processor
def inject_admin_status():
    """Inject admin login status into templates"""
    return {'admin_logged_in': session.get('admin_logged_in', False)}
