// Main JavaScript file for AsA WhatsApp System

// Global utility functions
function showAlert(message, type = 'info') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Insert at the top of main content
    const mainContent = document.querySelector('main .container');
    if (mainContent) {
        mainContent.insertAdjacentHTML('afterbegin', alertHtml);
    }
}

// Auto-hide alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Connection status monitoring
class ConnectionMonitor {
    constructor() {
        this.isMonitoring = false;
        this.interval = null;
    }
    
    start() {
        if (this.isMonitoring) return;
        
        this.isMonitoring = true;
        this.interval = setInterval(() => {
            this.checkStatus();
        }, 10000); // Check every 10 seconds
    }
    
    stop() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
        this.isMonitoring = false;
    }
    
    async checkStatus() {
        try {
            const response = await fetch('/connection_status');
            const data = await response.json();
            
            const statusElement = document.getElementById('connection-status');
            if (statusElement && data.is_connected) {
                // Reload page if connection status changed to connected
                if (!statusElement.innerHTML.includes('Conectado ao WhatsApp')) {
                    location.reload();
                }
            }
        } catch (error) {
            console.error('Error checking connection status:', error);
        }
    }
}

// Initialize connection monitor on relevant pages
const connectionMonitor = new ConnectionMonitor();
if (document.getElementById('connection-status')) {
    connectionMonitor.start();
}

// QR Code generation
async function generateQRCode() {
    const button = document.getElementById('generate-qr-btn');
    if (!button) return;
    
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Gerando...';
    button.disabled = true;
    
    try {
        const response = await fetch('/generate_qr');
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Erro ao gerar QR Code');
        }
        
        const qrDisplay = document.getElementById('qr-display');
        if (qrDisplay && data.qr_image) {
            qrDisplay.innerHTML = `
                <div class="qr-code-display text-center">
                    <img src="${data.qr_image}" alt="QR Code" class="qr-image mb-3" style="max-width: 300px; width: 100%;">
                    <p class="mt-2 mb-1 text-dark"><strong>Código gerado!</strong></p>
                    <small class="text-muted">Escaneie com seu WhatsApp</small>
                </div>
            `;
        } else {
            throw new Error('QR Code não disponível');
        }
        
        // Start monitoring for connection
        connectionMonitor.start();
        
        showAlert('Código QR gerado! Escaneie com seu WhatsApp.', 'success');
        
        // Mostrar botão de simular escaneamento para teste
        const simulateBtn = document.getElementById('simulate-scan-btn');
        if (simulateBtn) {
            simulateBtn.style.display = 'inline-block';
        }
        
    } catch (error) {
        console.error('Error generating QR code:', error);
        showAlert('Erro ao gerar código QR. Tente novamente.', 'danger');
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Test message functionality
async function sendTestMessage() {
    const messageInput = document.getElementById('test-message');
    const button = document.getElementById('send-test-btn');
    
    if (!messageInput || !button) return;
    
    const message = messageInput.value.trim();
    if (!message) {
        showAlert('Digite uma mensagem para testar.', 'warning');
        return;
    }
    
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Enviando...';
    button.disabled = true;
    
    try {
        const response = await fetch('/api/simulate_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                phone: '5511999999999',
                message: message,
                name: 'Usuário Teste'
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showAlert('Mensagem de teste enviada com sucesso! Verifique o painel admin.', 'success');
            messageInput.value = '';
        } else {
            throw new Error('Erro na resposta do servidor');
        }
        
    } catch (error) {
        console.error('Error sending test message:', error);
        showAlert('Erro ao enviar mensagem de teste.', 'danger');
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Simulate QR scan for testing
async function simulateScan() {
    const button = document.getElementById('simulate-scan-btn');
    if (!button) return;
    
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Conectando...';
    button.disabled = true;
    
    try {
        const response = await fetch('/simulate_scan');
        const data = await response.json();
        
        if (data.status === 'connected') {
            showAlert('WhatsApp conectado com sucesso!', 'success');
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            throw new Error('Erro na conexão');
        }
        
    } catch (error) {
        console.error('Error simulating scan:', error);
        showAlert('Erro ao simular escaneamento.', 'danger');
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // QR Code generation button
    const generateQRBtn = document.getElementById('generate-qr-btn');
    if (generateQRBtn) {
        generateQRBtn.addEventListener('click', generateQRCode);
    }
    
    // Test message button
    const sendTestBtn = document.getElementById('send-test-btn');
    if (sendTestBtn) {
        sendTestBtn.addEventListener('click', sendTestMessage);
    }
    
    // Simulate scan button
    const simulateScanBtn = document.getElementById('simulate-scan-btn');
    if (simulateScanBtn) {
        simulateScanBtn.addEventListener('click', simulateScan);
    }
    
    // Auto-focus on password field in login page
    const passwordField = document.getElementById('password');
    if (passwordField && window.location.pathname.includes('login')) {
        passwordField.focus();
    }
    
    // Form validation for response forms
    const responseForm = document.querySelector('form[action*="responses"]');
    if (responseForm) {
        responseForm.addEventListener('submit', function(e) {
            const keyword = document.getElementById('trigger_keyword');
            const response = document.getElementById('response_text');
            
            if (keyword && keyword.value.trim().length < 2) {
                e.preventDefault();
                showAlert('A palavra-chave deve ter pelo menos 2 caracteres.', 'warning');
                keyword.focus();
                return;
            }
            
            if (response && response.value.trim().length < 5) {
                e.preventDefault();
                showAlert('A resposta deve ter pelo menos 5 caracteres.', 'warning');
                response.focus();
                return;
            }
        });
    }
});

// Real-time updates for admin dashboard
class DashboardUpdater {
    constructor() {
        this.updateInterval = null;
    }
    
    start() {
        if (this.updateInterval) return;
        
        // Update every 30 seconds
        this.updateInterval = setInterval(() => {
            this.updateStats();
        }, 30000);
    }
    
    stop() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    async updateStats() {
        // This would fetch updated statistics
        // For now, we'll just refresh the page occasionally
        if (Math.random() < 0.1) { // 10% chance to refresh
            location.reload();
        }
    }
}

// Initialize dashboard updater on admin pages
if (window.location.pathname.includes('/admin/')) {
    const dashboardUpdater = new DashboardUpdater();
    dashboardUpdater.start();
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    connectionMonitor.stop();
});

// Toast notifications for better UX
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1055';
        document.body.appendChild(toastContainer);
    }
    
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div class="toast" id="${toastId}" role="alert">
            <div class="toast-header">
                <i class="fas fa-info-circle text-${type} me-2"></i>
                <strong class="me-auto">AsA</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

// Export for global use
window.AsA = {
    showAlert,
    showToast,
    generateQRCode,
    sendTestMessage,
    connectionMonitor
};
