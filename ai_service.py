import os
import logging
try:
    from google import genai
    from google.genai import types
    # Configure Gemini AI client only if API key is available
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
        types_available = True
    else:
        client = None
        types_available = False
        logging.warning("GEMINI_API_KEY not provided - AI features will be disabled")
except ImportError:
    genai = None
    client = None
    types = None
    types_available = False
    logging.warning("Google Genai library not available")

def get_custom_prompt():
    """Get custom AI prompt from database"""
    try:
        from app import app, db
        from models import SystemSettings
        
        with app.app_context():
            setting = SystemSettings.query.filter_by(setting_key='ai_prompt').first()
            if setting and setting.setting_value:
                return setting.setting_value
    except Exception as e:
        logging.error(f"Erro ao obter prompt personalizado: {e}")
    
    # Default prompt if none configured
    return """Você é um assistente virtual inteligente para WhatsApp.
Você deve responder de forma útil, amigável e profissional.

Instruções:
- Responda em português brasileiro
- Seja conciso mas informativo
- Mantenha um tom amigável e profissional
- Se não souber algo, seja honesto sobre isso
- Evite respostas muito longas para WhatsApp"""

def generate_ai_response(user_message: str, conversation_history=None) -> str:
    """
    Generate AI response using Gemini API
    
    Args:
        user_message: The user's message
        conversation_history: List of previous messages for context
    
    Returns:
        AI generated response
    """
    try:
        if not client:
            return "Desculpe, o serviço de IA não está disponível no momento."
            
        # Get custom prompt
        custom_prompt = get_custom_prompt()
        
        # Build context from conversation history
        context = ""
        if conversation_history:
            context = "Histórico da conversa:\n"
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                sender = "Usuário" if msg.is_from_user else "AsA"
                context += f"{sender}: {msg.content}\n"
            context += "\n"
        
        # Create prompt for AI
        prompt = f"""
        {custom_prompt}
        
        {context}
        
        Mensagem atual do usuário: {user_message}
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        if response.text:
            return response.text.strip()
        else:
            return "Desculpe, não consegui processar sua mensagem no momento. Tente novamente."
            
    except Exception as e:
        logging.error(f"Erro ao gerar resposta AI: {e}")
        return "Desculpe, estou com problemas técnicos. Tente novamente em alguns minutos."

def test_prompt_response(user_message: str, custom_prompt: str) -> str:
    """Test a prompt with a message without saving to database"""
    try:
        if not client:
            return "Serviço de IA não disponível"
            
        prompt = f"""
        {custom_prompt}
        
        Mensagem atual do usuário: {user_message}
        """
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        if response.text:
            return response.text.strip()
        else:
            return "Não consegui gerar resposta"
            
    except Exception as e:
        logging.error(f"Erro ao testar prompt: {e}")
        return f"Erro: {str(e)}"

def test_gemini_connection():
    """Test Gemini API connection"""
    try:
        # Re-initialize client with current API key
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"success": False, "error": "Nenhuma chave API configurada"}
        
        # Create new client instance
        test_client = genai.Client(api_key=api_key)
        
        # Test with a simple message
        test_prompt = "Responda apenas 'OK' para confirmar que você está funcionando."
        
        response = test_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=test_prompt
        )
        
        if response.text:
            return {"success": True, "response": response.text.strip()}
        else:
            return {"success": False, "error": "API não retornou resposta"}
            
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
            return {"success": False, "error": "Chave API inválida"}
        elif "quota" in error_msg.lower():
            return {"success": False, "error": "Cota da API excedida"}
        else:
            return {"success": False, "error": f"Erro de conexão: {error_msg}"}

def analyze_message_intent(message: str) -> dict:
    """
    Analyze message intent to determine best response strategy
    
    Returns:
        Dict with intent analysis results
    """
    try:
        if not client or not types_available:
            return {"tipo": "outro", "urgencia": "baixo", "requer_humano": False}
            
        prompt = f"""
        Analise a seguinte mensagem do WhatsApp e determine:
        1. Se é uma pergunta, saudação, pedido de informação, reclamação, etc.
        2. O nível de urgência (baixo, médio, alto)
        3. Se requer resposta humana ou pode ser respondida automaticamente
        
        Mensagem: "{message}"
        
        Responda apenas com JSON no formato:
        {{"tipo": "pergunta|saudacao|pedido|reclamacao|outro", "urgencia": "baixo|medio|alto", "requer_humano": true|false}}
        """
        
        if types:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
        else:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
        
        if response.text:
            import json
            return json.loads(response.text)
        else:
            return {"tipo": "outro", "urgencia": "baixo", "requer_humano": False}
            
    except Exception as e:
        logging.error(f"Erro ao analisar intenção da mensagem: {e}")
        return {"tipo": "outro", "urgencia": "baixo", "requer_humano": False}
