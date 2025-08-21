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
                
                # Verificar se já existe um processo rodando na porta 3001
                try:
                    response = requests.get('http://localhost:3001/status', timeout=2)
                    if response.status_code == 200:
                        logging.info("✅ Serviço Baileys já está rodando!")
                        self.is_running = True
                        return
                except:
                    pass  # Continuar para iniciar o serviço
                
                # Iniciar o processo Node.js
                self.process = subprocess.Popen(
                    ['node', 'whatsapp_baileys_simple.js'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    preexec_fn=os.setsid if os.name != 'nt' else None
                )
                
                # Aguardar o serviço iniciar
                for _ in range(10):  # Tentar por 10 segundos
                    time.sleep(1)
                    try:
                        response = requests.get('http://localhost:3001/status', timeout=2)
                        if response.status_code == 200:
                            self.is_running = True
                            logging.info("✅ Serviço Baileys iniciado com sucesso!")
                            return
                    except:
                        continue
                
                # Se chegou aqui, o serviço não iniciou
                logging.error("❌ Falha ao iniciar serviço Baileys - timeout")
                self.is_running = False
                if self.process:
                    self.process.terminate()
                
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
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, retries: int = 2) -> Dict:
        """Fazer requisição para o serviço Baileys com retry"""
        last_error = None
        
        for attempt in range(retries + 1):
            try:
                # Verificar se o serviço está rodando
                if not self.is_running or attempt > 0:
                    self.start_baileys_service()
                
                url = f"{self.base_url}{endpoint}"
                
                if method.upper() == 'GET':
                    response = requests.get(url, timeout=8)
                elif method.upper() == 'POST':
                    response = requests.post(url, json=data or {}, timeout=8)
                else:
                    return {"success": False, "error": "Método não suportado"}
                
                if response.status_code == 200:
                    result = response.json()
                    self.is_running = True  # Confirmar que está rodando
                    return result
                else:
                    return {"success": False, "error": f"Status {response.status_code}: {response.text}"}
                    
            except requests.exceptions.ConnectionError as e:
                last_error = "Serviço WhatsApp não está rodando"
                self.is_running = False
            except requests.exceptions.Timeout as e:
                last_error = "Timeout na conexão"
            except Exception as e:
                last_error = str(e)
                
            # Se não é a última tentativa, aguardar um pouco
            if attempt < retries:
                time.sleep(2)
        
        return {"success": False, "error": last_error or "Erro desconhecido"}
    
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