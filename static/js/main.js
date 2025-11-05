// Main JavaScript for RiF Activator A12+
// This file is served to complete the PWA setup

console.log('RiF Activator A12+ - JavaScript loaded successfully');

// PWA Install functionality
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    showInstallButton();
});

function showInstallButton() {
    const installButton = document.createElement('button');
    installButton.innerHTML = '<i class="fas fa-download"></i> تثبيت التطبيق';
    installButton.className = 'install-button';
    installButton.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: #4CAF50;
        color: white;
        border: none;
        padding: 12px 20px;
        border-radius: 25px;
        cursor: pointer;
        font-family: 'Cairo', sans-serif;
        font-weight: 600;
        z-index: 1000;
        box-shadow: 0 4px 20px rgba(76, 175, 80, 0.3);
        transition: all 0.3s ease;
    `;
    
    installButton.addEventListener('click', async () => {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            if (outcome === 'accepted') {
                console.log('PWA installed successfully');
            }
            deferredPrompt = null;
            installButton.remove();
        }
    });
    
    document.body.appendChild(installButton);
}