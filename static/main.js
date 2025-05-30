// Global error logging to backend
window.onerror = function (message, source, lineno, colno, error) {
    console.error("Captured error:", { message, source, lineno, colno, error });
    fetch('/frontend_error_log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            type: 'window.onerror',
            message, source, lineno, colno,
            stack: error && error.stack,
            userAgent: navigator.userAgent,
            url: window.location.href,
            timestamp: new Date().toISOString()
        })
    });
};

window.addEventListener('unhandledrejection', function (event) {
    fetch('/frontend_error_log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            type: 'unhandledrejection',
            reason: event.reason && event.reason.toString(),
            stack: event.reason && event.reason.stack,
            userAgent: navigator.userAgent,
            url: window.location.href,
            timestamp: new Date().toISOString()
        })
    });
});

// Debug: Kontrollera att main.js laddas och att knapparna finns
console.log("main.js loaded");

document.addEventListener('DOMContentLoaded', function () {
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    console.log("startBtn:", startBtn, "stopBtn:", stopBtn);

    if (startBtn) {
        startBtn.addEventListener('click', function () {
            console.log("Start button clicked!");
                        fetch('/start', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    document.getElementById('bot-control-status').textContent = 'Bot startad!';
                })
                .catch(err => {
                    document.getElementById('bot-control-status').textContent = 'Fel vid start!';
                    console.error(err);
                });
        });
    }
    if (stopBtn) {
        stopBtn.addEventListener('click', function () {
            console.log("Stop button clicked!");
            fetch('/stop', { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    document.getElementById('bot-control-status').textContent = 'Bot stoppad!';
                })
                .catch(err => {
                    document.getElementById('bot-control-status').textContent = 'Fel vid stopp!';
                    console.error(err);
                });
        });
    }
});