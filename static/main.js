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