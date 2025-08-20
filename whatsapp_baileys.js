const { default: makeWASocket, DisconnectReason, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const QRCode = require('qrcode');
const express = require('express');
const axios = require('axios');
const fs = require('fs');
const path = require('path');

// Configuração do servidor Express
const app = express();
app.use(express.json());

// Estado da conexão WhatsApp
let socket = null;
let qrCodeData = null;
let isConnected = false;
let connectionStatus = 'disconnected';

// URL do servidor Python Flask
const FLASK_SERVER = 'http://localhost:5000';

// Função para notificar o Flask sobre mudanças de status
async function notifyFlask(endpoint, data) {
    try {
        await axios.post(`${FLASK_SERVER}${endpoint}`, data, {
            headers: { 'Content-Type': 'application/json' }
        });
    } catch (error) {
        console.log('Erro ao notificar Flask:', error.message);
    }
}

// Função para conectar ao WhatsApp
async function connectToWhatsApp() {
    try {
        // Usar autenticação multi-file para persistir a sessão
        const { state, saveCreds } = await useMultiFileAuthState('./auth_info');
        
        socket = makeWASocket({
            auth: state,
            printQRInTerminal: false,
            logger: { level: 'silent' }
        });

        // Eventos da conexão
        socket.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;
            
            if (qr) {
                console.log('🔗 QR Code gerado');
                qrCodeData = qr;
                connectionStatus = 'qr_ready';
                
                // Notificar Flask que QR está pronto
                await notifyFlask('/webhook/qr-ready', { qr_code: qr });
            }
            
            if (connection === 'close') {
                const shouldReconnect = (lastDisconnect?.error)?.output?.statusCode !== DisconnectReason.loggedOut;
                console.log('🔌 Conexão fechada. Reconectar?', shouldReconnect);
                isConnected = false;
                connectionStatus = 'disconnected';
                
                await notifyFlask('/webhook/disconnected', { reason: 'connection_closed' });
                
                if (shouldReconnect) {
                    setTimeout(connectToWhatsApp, 3000);
                }
            } else if (connection === 'open') {
                console.log('✅ WhatsApp conectado com sucesso!');
                isConnected = true;
                connectionStatus = 'connected';
                qrCodeData = null;
                
                await notifyFlask('/webhook/connected', { 
                    phone: socket.user?.id?.split(':')[0] || 'unknown',
                    user: socket.user 
                });
            }
        });

        // Salvar credenciais quando atualizadas
        socket.ev.on('creds.update', saveCreds);

        // Receber mensagens
        socket.ev.on('messages.upsert', async (m) => {
            const message = m.messages[0];
            
            if (!message.key.fromMe && message.message) {
                const phoneNumber = message.key.remoteJid;
                const messageText = message.message.conversation || 
                                 message.message.extendedTextMessage?.text || '';
                
                if (messageText) {
                    console.log(`📨 Mensagem recebida de ${phoneNumber}: ${messageText}`);
                    
                    // Enviar para Flask processar
                    await notifyFlask('/webhook/message-received', {
                        phone: phoneNumber.replace('@s.whatsapp.net', ''),
                        message: messageText,
                        contact_name: message.pushName || '',
                        message_id: message.key.id,
                        timestamp: new Date().toISOString()
                    });
                }
            }
        });

    } catch (error) {
        console.error('❌ Erro ao conectar WhatsApp:', error);
        connectionStatus = 'error';
        await notifyFlask('/webhook/error', { error: error.message });
    }
}

// API Routes
app.get('/status', (req, res) => {
    res.json({
        connected: isConnected,
        status: connectionStatus,
        qr_available: !!qrCodeData,
        user: socket?.user || null
    });
});

app.get('/qr', async (req, res) => {
    if (qrCodeData) {
        try {
            const qrImage = await QRCode.toDataURL(qrCodeData);
            res.json({
                success: true,
                qr_code: qrCodeData,
                qr_image: qrImage
            });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    } else {
        res.json({ success: false, message: 'QR Code não disponível' });
    }
});

app.post('/send-message', async (req, res) => {
    const { phone, message } = req.body;
    
    if (!isConnected) {
        return res.status(400).json({ error: 'WhatsApp não conectado' });
    }
    
    try {
        const jid = phone.includes('@') ? phone : `${phone}@s.whatsapp.net`;
        await socket.sendMessage(jid, { text: message });
        
        console.log(`📤 Mensagem enviada para ${phone}: ${message}`);
        res.json({ success: true, message: 'Mensagem enviada' });
    } catch (error) {
        console.error('❌ Erro ao enviar mensagem:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/connect', async (req, res) => {
    if (!isConnected) {
        await connectToWhatsApp();
        res.json({ success: true, message: 'Iniciando conexão...' });
    } else {
        res.json({ success: true, message: 'Já conectado' });
    }
});

app.post('/disconnect', async (req, res) => {
    if (socket) {
        await socket.logout();
        socket = null;
        isConnected = false;
        connectionStatus = 'disconnected';
        qrCodeData = null;
    }
    res.json({ success: true, message: 'Desconectado' });
});

// Iniciar servidor
const PORT = 3001;
app.listen(PORT, () => {
    console.log(`🚀 Servidor Baileys rodando na porta ${PORT}`);
    console.log(`📱 WhatsApp Service iniciado`);
    
    // Conectar automaticamente ao iniciar
    setTimeout(connectToWhatsApp, 1000);
});

// Tratamento de erros não capturados
process.on('uncaughtException', (error) => {
    console.error('❌ Erro não capturado:', error);
});

process.on('unhandledRejection', (error) => {
    console.error('❌ Promise rejeitada:', error);
});