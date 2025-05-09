document.addEventListener('DOMContentLoaded', function() {
    // Hämta och visa saldo
    fetch('/balance').then(r => r.json()).then(data => {
        document.getElementById('balance').innerText = 'Saldo: ' + JSON.stringify(data);
    });
    // Hämta och visa orderhistorik
    fetch('/orderhistory').then(r => r.json()).then(data => {
        document.getElementById('orderhistory').innerText = 'Orderhistorik: ' + JSON.stringify(data);
    });
    // Hämta och visa öppna ordrar
    fetch('/openorders').then(r => r.json()).then(data => {
        document.getElementById('openorders').innerText = 'Öppna ordrar: ' + JSON.stringify(data);
    });
    // Hämta och visa strategi-prestanda
    fetch('/strategy_performance').then(r => r.json()).then(data => {
        document.getElementById('performance').innerText = 'Strategi-prestanda: ' + JSON.stringify(data);
    });

    // Botstyrning
    document.getElementById('startBtn').onclick = function() {
        fetch('/start', {method: 'POST'}).then(r => r.json()).then(data => {
            document.getElementById('status').innerText = 'Status: ' + data.status;
        });
    };
    document.getElementById('stopBtn').onclick = function() {
        fetch('/stop', {method: 'POST'}).then(r => r.json()).then(data => {
            document.getElementById('status').innerText = 'Status: ' + data.status;
        });
    };
    fetch('/status').then(r => r.json()).then(data => {
        document.getElementById('status').innerText = 'Status: ' + data.status;
    });
    // Orderformulär
    document.getElementById('orderForm').onsubmit = function(e) {
        e.preventDefault();
        const symbol = document.getElementById('symbol').value;
        const type = document.getElementById('orderType').value;
        const amount = document.getElementById('amount').value;
        const price = document.getElementById('price').value;
        const payload = {symbol, type, amount};
        if (price) payload.price = price;
        fetch('/order', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        }).then(r => r.json()).then(data => {
            document.getElementById('orderResult').innerText = JSON.stringify(data);
        });
    };
});
