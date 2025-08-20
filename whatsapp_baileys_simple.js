const { default: makeWASocket, DisconnectReason, useMultiFileAuthState, downloadMediaMessage } = require('@whiskeysockets/baileys');
const QRCode = require('qrcode');
const express = require('express');
const axios = require('axios');
const fs = require('fs');
const http = require('http');

// Servidor Express simples
const app = express();
app.use(express.json());

// Estado da aplicação
let socket = null;
let qrCodeData = null;
let isConnected = false;
let connectionStatus = 'disconnected';
let userInfo = null;

console.log('🚀 Iniciando WhatsApp Service...');

// Função para notificar o Flask
async function notifyFlask(endpoint, data) {
    try {
        await axios.post(`http://localhost:5000${endpoint}`, data, {
            headers: { 'Content-Type': 'application/json' },
            timeout: 3000
        });
    } catch (error) {
        // Ignorar erros de notificação
    }
}

// Conectar ao WhatsApp
async function connectToWhatsApp() {
    try {
        console.log('📱 Conectando ao WhatsApp...');
        
        // Usar pasta de auth local
        const { state, saveCreds } = await useMultiFileAuthState('./whatsapp_auth');
        
        socket = makeWASocket({
            auth: state,
            printQRInTerminal: false,
            // Remove logger config to use default
            browser: ['AsA WhatsApp Bot', 'Chrome', '1.0.0']
        });

        // Evento de atualização de conexão
        socket.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;
            
            if (qr) {
                console.log('🔗 QR Code gerado!');
                qrCodeData = qr;
                connectionStatus = 'qr_ready';
                
                // Notificar Flask que QR está pronto
                await notifyFlask('/api/qr-updated', { qr_code: qr });
            }
            
            if (connection === 'close') {
                const shouldReconnect = (lastDisconnect?.error)?.output?.statusCode !== DisconnectReason.loggedOut;
                console.log('🔌 Conexão fechada. Reconectar?', shouldReconnect);
                
                isConnected = false;
                connectionStatus = 'disconnected';
                qrCodeData = null;
                userInfo = null;
                
                await notifyFlask('/api/disconnected', { reason: 'connection_closed' });
                
                if (shouldReconnect) {
                    console.log('🔄 Reconectando em 3 segundos...');
                    setTimeout(connectToWhatsApp, 3000);
                }
            } else if (connection === 'open') {
                console.log('✅ WhatsApp conectado com sucesso!');
                isConnected = true;
                connectionStatus = 'connected';
                qrCodeData = null;
                userInfo = socket.user;
                
                await notifyFlask('/api/connected', { 
                    phone: socket.user?.id?.split(':')[0] || 'unknown',
                    user: socket.user 
                });
            }
        });

        // Salvar credenciais
        socket.ev.on('creds.update', saveCreds);

        // Receber mensagens
        socket.ev.on('messages.upsert', async (m) => {
            const message = m.messages[0];
            
            if (!message.key.fromMe && message.message) {
                const phoneNumber = message.key.remoteJid;
                
                // Extrair texto da mensagem
                let messageText = '';
                if (message.message.conversation) {
                    messageText = message.message.conversation;
                } else if (message.message.extendedTextMessage) {
                    messageText = message.message.extendedTextMessage.text;
                }
                
                if (messageText && phoneNumber) {
                    const cleanPhone = phoneNumber.replace('@s.whatsapp.net', '');
                    console.log(`📨 Mensagem de ${cleanPhone}: ${messageText}`);
                    
                    // Enviar para Flask processar
                    await notifyFlask('/api/message-received', {
                        phone: cleanPhone,
                        message: messageText,
                        contact_name: message.pushName || '',
                        message_id: message.key.id,
                        timestamp: new Date().toISOString()
                    });
                }
            }
        });

    } catch (error) {
        console.error('❌ Erro ao conectar:', error);
        connectionStatus = 'error';
        setTimeout(connectToWhatsApp, 5000);
    }
}

// API Routes
app.get('/status', (req, res) => {
    res.json({
        connected: isConnected,
        status: connectionStatus,
        qr_available: !!qrCodeData,
        user: userInfo
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
    
    if (!isConnected || !socket) {
        return res.status(400).json({ error: 'WhatsApp não conectado' });
    }
    
    try {
        let jid = phone;
        if (!phone.includes('@')) {
            // Limpar número e adicionar @s.whatsapp.net
            const cleanPhone = phone.replace(/\D/g, '');
            jid = `${cleanPhone}@s.whatsapp.net`;
        }
        
        await socket.sendMessage(jid, { text: message });
        
        console.log(`📤 Mensagem enviada para ${phone}: ${message}`);
        res.json({ success: true, message: 'Mensagem enviada' });
    } catch (error) {
        console.error('❌ Erro ao enviar mensagem:', error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/set-typing', async (req, res) => {
    const { phone, typing = true } = req.body;
    
    if (!isConnected || !socket) {
        return res.status(400).json({ error: 'WhatsApp não conectado' });
    }
    
    try {
        let jid = phone;
        if (!phone.includes('@')) {
            const cleanPhone = phone.replace(/\D/g, '');
            jid = `${cleanPhone}@s.whatsapp.net`;
        }
        
        await socket.sendPresenceUpdate(typing ? 'composing' : 'paused', jid);
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Iniciar servidor
const PORT = 3001;
const server = app.listen(PORT, () => {
    console.log(`🚀 WhatsApp Service rodando na porta ${PORT}`);
    
    // Conectar automaticamente
    setTimeout(connectToWhatsApp, 1000);
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('🛑 Encerrando WhatsApp Service...');
    if (socket) {
        await socket.logout();
    }
    server.close(() => {
        console.log('✅ Servidor encerrado');
        process.exit(0);
    });
});

process.on('uncaughtException', (error) => {
    console.error('❌ Erro não capturado:', error);
});

process.on('unhandledRejection', (error) => {
    console.error('❌ Promise rejeitada:', error);
});