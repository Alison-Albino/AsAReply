import os
import logging
try:
    from google import genai
    from google.genai import types
    # Configure Gemini AI client
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    types_available = True
except ImportError:
    genai = None
    client = None
    types = None
    types_available = False
    logging.warning("Google Genai library not available")

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
        Você é o AsA (Assistente Automático), um assistente virtual inteligente para WhatsApp.
        Você deve responder de forma útil, amigável e profissional.
        
        {context}
        
        Mensagem atual do usuário: {user_message}
        
        Instruções:
        - Responda em português brasileiro
        - Seja conciso mas informativo
        - Mantenha um tom amigável e profissional
        - Se não souber algo, seja honesto sobre isso
        - Evite respostas muito longas para WhatsApp
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
