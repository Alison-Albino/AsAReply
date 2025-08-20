import os
import requests
import logging
import subprocess
import threading
import time
from typing import Dict, Optional

class BaileysService:
    """Serviço para gerenciar o WhatsApp via Baileys local"""
    
    def __init__(self):
        self.base_url = 'http://localhost:3001'
        self.process = None
        self.is_running = False
        
        # Iniciar o serviço Node.js automaticamente
        self.start_baileys_service()
    
    def start_baileys_service(self):
        """Iniciar o serviço Baileys em background"""
        try:
            if not self.is_running:
                logging.info("🚀 Iniciando serviço Baileys...")
                
                # Verificar se Node.js está disponível
                result = subprocess.run(['node', '--version'], capture_output=True, text=True)
                if result.returncode != 0:
                    logging.error("Node.js não encontrado!")
                    return
                
                # Iniciar o processo Node.js
                self.process = subprocess.Popen(
                    ['node', 'whatsapp_baileys_simple.js'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                self.is_running = True
                
                # Aguardar um pouco para o serviço iniciar
                time.sleep(3)
                
                # Verificar se está rodando
                if self.process.poll() is None:
                    logging.info("✅ Serviço Baileys iniciado com sucesso!")
                else:
                    logging.error("❌ Falha ao iniciar serviço Baileys")
                    self.is_running = False
                
        except Exception as e:
            logging.error(f"Erro ao iniciar Baileys: {e}")
            self.is_running = False
    
    def stop_baileys_service(self):
        """Parar o serviço Baileys"""
        try:
            if self.process and self.process.poll() is None:
                logging.info("🛑 Parando serviço Baileys...")
                self.process.terminate()
                self.process.wait(timeout=5)
                self.is_running = False
                logging.info("✅ Serviço Baileys parado")
        except Exception as e:
            logging.error(f"Erro ao parar Baileys: {e}")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Fazer requisição para o serviço Baileys"""
        try:
            if not self.is_running:
                self.start_baileys_service()
                time.sleep(2)
            
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == 'GET':
                response = requests.get(url, timeout=10)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data or {}, timeout=10)
            else:
                return {"success": False, "error": "Método não suportado"}
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"Status {response.status_code}: {response.text}"}
                
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Serviço WhatsApp não está rodando"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Timeout na conexão"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_connection_status(self) -> Dict:
        """Obter status da conexão"""
        return self._make_request('GET', '/status')
    
    def get_qr_code(self) -> Dict:
        """Obter QR Code"""
        return self._make_request('GET', '/qr')
    
    def send_message(self, phone: str, message: str) -> Dict:
        """Enviar mensagem"""
        return self._make_request('POST', '/send-message', {
            'phone': phone,
            'message': message
        })
    
    def set_typing(self, phone: str, typing: bool = True) -> Dict:
        """Definir status de digitação"""
        return self._make_request('POST', '/set-typing', {
            'phone': phone,
            'typing': typing
        })

# Instância global
baileys_service = BaileysService()