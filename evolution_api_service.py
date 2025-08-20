import os
import requests
import logging
import json
from datetime import datetime
from typing import Dict, Optional

class EvolutionAPIService:
    """Serviço para integração com Evolution API"""
    
    def __init__(self):
        # Configurações da Evolution API
        self.base_url = os.environ.get('EVOLUTION_API_URL', 'http://localhost:8080')
        self.api_key = os.environ.get('EVOLUTION_API_KEY', 'B6D711FCDE4D4FD5936544120E713976')
        self.instance_name = os.environ.get('EVOLUTION_INSTANCE_NAME', 'asa_whatsapp')
        
        self.headers = {
            'Content-Type': 'application/json',
            'apikey': self.api_key
        }
        
        logging.info(f"Evolution API configurada: {self.base_url}")
    
    def create_instance(self) -> Dict:
        """Criar uma nova instância do WhatsApp"""
        try:
            url = f"{self.base_url}/instance/create"
            data = {
                "instanceName": self.instance_name,
                "token": self.api_key,
                "qrcode": True,
                "webhookUrl": f"{os.environ.get('WEBHOOK_URL', 'http://localhost:5000')}/webhook/evolution",
                "webhookByEvents": True,
                "webhookBase64": False,
                "events": [
                    "APPLICATION_STARTUP",
                    "QRCODE_UPDATED", 
                    "CONNECTION_UPDATE",
                    "MESSAGES_UPSERT",
                    "MESSAGES_UPDATE",
                    "SEND_MESSAGE"
                ]
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 201:
                result = response.json()
                logging.info(f"Instância criada: {result}")
                return {"success": True, "data": result}
            else:
                logging.error(f"Erro ao criar instância: {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logging.error(f"Erro ao criar instância: {e}")
            return {"success": False, "error": str(e)}
    
    def get_connection_state(self) -> Dict:
        """Obter estado da conexão"""
        try:
            url = f"{self.base_url}/instance/connectionState/{self.instance_name}"
            response = requests.get(url, headers=self.headers, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                return {"success": True, "data": result}
            else:
                return {"success": False, "error": response.text}
                
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Evolution API não está rodando. Configure em /evolution-setup"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Timeout ao conectar com Evolution API"}
        except Exception as e:
            logging.error(f"Erro ao obter estado da conexão: {e}")
            return {"success": False, "error": str(e)}
    
    def get_qr_code(self) -> Dict:
        """Obter código QR para conexão"""
        try:
            url = f"{self.base_url}/instance/connect/{self.instance_name}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                if 'qrcode' in result:
                    return {
                        "success": True, 
                        "qr_code": result.get('qrcode', {}).get('code', ''),
                        "qr_base64": result.get('qrcode', {}).get('base64', '')
                    }
                else:
                    return {"success": False, "error": "QR Code não disponível"}
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logging.error(f"Erro ao obter QR Code: {e}")
            return {"success": False, "error": str(e)}
    
    def send_message(self, phone: str, message: str) -> Dict:
        """Enviar mensagem via Evolution API"""
        try:
            # Garantir formato correto do número
            if not phone.endswith('@s.whatsapp.net'):
                # Remover caracteres especiais e adicionar código do país se necessário
                clean_phone = ''.join(filter(str.isdigit, phone))
                if not clean_phone.startswith('55'):  # Brasil
                    clean_phone = '55' + clean_phone
                phone = f"{clean_phone}@s.whatsapp.net"
            
            url = f"{self.base_url}/message/sendText/{self.instance_name}"
            data = {
                "number": phone,
                "text": message
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 201:
                result = response.json()
                logging.info(f"Mensagem enviada para {phone}: {message[:50]}...")
                return {"success": True, "data": result}
            else:
                logging.error(f"Erro ao enviar mensagem: {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logging.error(f"Erro ao enviar mensagem: {e}")
            return {"success": False, "error": str(e)}
    
    def set_typing(self, phone: str, typing: bool = True) -> Dict:
        """Simular digitação"""
        try:
            if not phone.endswith('@s.whatsapp.net'):
                clean_phone = ''.join(filter(str.isdigit, phone))
                if not clean_phone.startswith('55'):
                    clean_phone = '55' + clean_phone
                phone = f"{clean_phone}@s.whatsapp.net"
            
            url = f"{self.base_url}/chat/presence/{self.instance_name}"
            data = {
                "number": phone,
                "presence": "composing" if typing else "paused"
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            return {"success": response.status_code == 201}
            
        except Exception as e:
            logging.error(f"Erro ao definir digitação: {e}")
            return {"success": False, "error": str(e)}
    
    def disconnect_instance(self) -> Dict:
        """Desconectar instância"""
        try:
            url = f"{self.base_url}/instance/logout/{self.instance_name}"
            response = requests.delete(url, headers=self.headers)
            
            if response.status_code == 200:
                return {"success": True, "message": "Instância desconectada"}
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logging.error(f"Erro ao desconectar instância: {e}")
            return {"success": False, "error": str(e)}
    
    def get_instance_info(self) -> Dict:
        """Obter informações da instância"""
        try:
            url = f"{self.base_url}/instance/fetchInstances"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                instances = response.json()
                for instance in instances:
                    if instance.get('instanceName') == self.instance_name:
                        return {"success": True, "data": instance}
                
                return {"success": False, "error": "Instância não encontrada"}
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logging.error(f"Erro ao obter informações da instância: {e}")
            return {"success": False, "error": str(e)}

# Instância global do serviço
evolution_service = EvolutionAPIService()