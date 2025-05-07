/**
 * strategy_performance.js
 * 
 * Hanterar strategi-prestanda-sektionen med utökade statistik- och debugfunktioner
 */

document.addEventListener('DOMContentLoaded', function() {
    // Variabeldeklarationer för diagram
    let performanceOverviewChart = null;
    let dailyPerformanceChart = null;
    let hourlyActivityChart = null;
    
    // Formaterings-hjälpfunktioner
    function formatCurrency(amount) {
        return new Intl.NumberFormat('sv-SE', { 
            style: 'currency', 
            currency: 'USD',
            minimumFractionDigits: 2
        }).format(amount);
    }
    
    function formatPercent(value) {
        return new Intl.NumberFormat('sv-SE', { 
            style: 'percent', 
            minimumFractionDigits: 1,
            maximumFractionDigits: 1
        }).format(value / 100);
    }
    
    function formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('sv-SE');
    }
    
    function formatDateTime(dateTimeString) {
        if (!dateTimeString) return '-';
        const date = new Date(dateTimeString);
        return date.toLocaleString('sv-SE');
    }
    
    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
    
    // Hitta formulär-referens
    const performanceFilterForm = document.getElementById('performance-filter-form');
    
    // Hämta strategi-prestanda från API
    function fetchStrategyPerformance() {
        const apiBase = window.location.origin;
        const params = new URLSearchParams();
        
        // Hämta filtervärden
        const symbol = document.getElementById('performance-symbol')?.value || '';
        const startDate = document.getElementById('performance-start-date')?.value || '';
        const endDate = document.getElementById('performance-end-date')?.value || '';
        const detailLevel = document.getElementById('detail-level')?.value || 'standard';
        
        // Lägg till i query params
        if (symbol) params.append('symbol', symbol);
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        params.append('detail_level', detailLevel);
        
        // Skapa URL
        const url = `${apiBase}/strategy_performance?${params.toString()}`;
        
        // Visa laddningsindikator
        document.getElementById('total-trades').textContent = 'Laddar...';
        
        // Hämta data
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'ok') {
                    // Visa data i gränssnittet
                    displayPerformanceData(data.performance, data.trades);
                    
                    // Visa debugdata om den finns och detaljnivån är 'full'
                    if (detailLevel === 'full') {
                        document.getElementById('debug-section').style.display = 'block';
                        if (data.parse_errors) {
                            document.getElementById('parse-errors').textContent = 
                                JSON.stringify(data.parse_errors, null, 2);
                        }
                    } else {
                        document.getElementById('debug-section').style.display = 'none';
                    }
                    
                    // Visa utökad statistik om detaljnivån är 'extended' eller 'full'
                    if (detailLevel === 'extended' || detailLevel === 'full') {
                        document.getElementById('extended-stats').style.display = 'block';
                    } else {
                        document.getElementById('extended-stats').style.display = 'none';
                    }
                } else {
                    console.error('Fel vid hämtning av statistik:', data.status);
                    alert(`Ett fel uppstod: ${data.status}`);
                }
            })
            .catch(error => {
                console.error('Fel vid API-anrop:', error);
                alert(`Ett fel uppstod: ${error.message}`);
            });
    }
    
    // Hämta debug-log från API
    function fetchDebugLog() {
        const apiBase = window.location.origin;
        const url = `${apiBase}/debug_log`;
        
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                updateDebugInfo(data);
            })
            .catch(error => {
                console.error('Fel vid hämtning av debuglog:', error);
            });
    }
    
    // Visa prestanda-data i gränssnittet
    function displayPerformanceData(performance, trades) {
        // Uppdatera grundläggande statistikvärden
        document.getElementById('total-trades').textContent = performance.total_trades || 0;
        document.getElementById('total-buys').textContent = performance.buys || 0;
        document.getElementById('total-sells').textContent = performance.sells || 0;
        document.getElementById('total-executed').textContent = performance.executed || 0;
        document.getElementById('total-cancelled').textContent = performance.cancelled || 0;
        
        // P&L och lönsamhet
        const profitLoss = document.getElementById('profit-loss');
        profitLoss.textContent = formatCurrency(performance.profit_loss || 0);
        profitLoss.className = (performance.profit_loss || 0) >= 0 ? 'positive' : 'negative';
        
        const avgProfit = document.getElementById('avg-profit');
        avgProfit.textContent = formatCurrency(performance.avg_profit_per_trade || 0);
        avgProfit.className = (performance.avg_profit_per_trade || 0) >= 0 ? 'positive' : 'negative';
        
        document.getElementById('win-rate').textContent = ((performance.win_rate || 0) + '%');
        document.getElementById('trade-frequency').textContent = (performance.trade_frequency || 0).toFixed(1);
        document.getElementById('risk-reward').textContent = (performance.risk_reward_ratio || 0).toFixed(2);
        
        // Utökad statistik
        if (performance.highest_profit_trade) {
            document.getElementById('top-profit-trade').textContent = 
                `${performance.highest_profit_trade.symbol} ${formatCurrency(performance.highest_profit_trade.value || 0)}`;
        }
        
        if (performance.highest_loss_trade) {
            document.getElementById('top-loss-trade').textContent = 
                `${performance.highest_loss_trade.symbol} ${formatCurrency(performance.highest_loss_trade.value || 0)}`;
        }
        
        document.getElementById('active-streak').textContent = performance.current_streak || 0;
        document.getElementById('longest-win-streak').textContent = performance.consecutive_wins || 0;
        
        // Uppdatera symbolprestandatabell
        updateSymbolPerformanceTable(performance.symbols || {});
        
        // Uppdatera trades-tabell
        updateTradesTable(trades || []);
        
        // Uppdatera diagram
        updatePerformanceOverviewChart(performance);
        updateDailyPerformanceChart(performance.daily_performance || []);
        updateHourlyActivityChart(performance.trade_success_by_hour || {});
    }
    
    // Uppdatera symbolprestandatabell
    function updateSymbolPerformanceTable(symbols) {
        const table = document.getElementById('symbol-performance-table');
        table.innerHTML = '';
        
        if (Object.keys(symbols).length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="6">Ingen data tillgänglig</td>';
            table.appendChild(row);
            return;
        }
        
        for (const [symbol, stats] of Object.entries(symbols)) {
            const row = document.createElement('tr');
            const profitLossClass = (stats.profit_loss || 0) >= 0 ? 'positive' : 'negative';
            
            row.innerHTML = `
                <td>${symbol}</td>
                <td>${stats.trades || 0}</td>
                <td>${stats.buys || 0}</td>
                <td>${stats.sells || 0}</td>
                <td>${(stats.volume || 0).toFixed(2)}</td>
                <td>${stats.executed || 0}</td>
            `;
            table.appendChild(row);
        }
    }
    
    // Uppdatera trades-tabell
    function updateTradesTable(trades) {
        const table = document.getElementById('performance-trades-table');
        table.innerHTML = '';
        
        if (trades.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="7">Inga trades hittades</td>';
            table.appendChild(row);
            return;
        }
        
        trades.slice(0, 20).forEach(trade => {
            const row = document.createElement('tr');
            
            let statusClass = '';
            if (trade.status) {
                if (trade.status.toUpperCase().includes('EXECUTED')) {
                    statusClass = 'status-executed';
                } else if (trade.status.toUpperCase().includes('CANCELLED') || 
                          trade.status.toUpperCase().includes('CANCELED')) {
                    statusClass = 'status-canceled';
                } else {
                    statusClass = 'status-other';
                }
            }
            
            row.innerHTML = `
                <td>${trade.time || '-'}</td>
                <td>${trade.symbol || '-'}</td>
                <td>${trade.side === 'buy' ? 'Köp' : 'Sälj'}</td>
                <td>${(trade.price || 0).toFixed(2)}</td>
                <td>${(trade.amount || 0).toFixed(6)}</td>
                <td>${formatCurrency(trade.value || 0)}</td>
                <td class="${statusClass}">${trade.status || '-'}</td>
            `;
            table.appendChild(row);
        });
    }
    
    // Uppdatera översiktsdiagram
    function updatePerformanceOverviewChart(performance) {
        const ctx = document.getElementById('performance-overview-chart').getContext('2d');
        
        if (performanceOverviewChart) {
            performanceOverviewChart.destroy();
        }
        
        performanceOverviewChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Köp', 'Sälj', 'Utförda', 'Avbrutna'],
                datasets: [{
                    data: [
                        performance.buys || 0, 
                        performance.sells || 0, 
                        performance.executed || 0, 
                        performance.cancelled || 0
                    ],
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.7)',
                        'rgba(255, 99, 132, 0.7)',
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(255, 159, 64, 0.7)'
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 99, 132, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(255, 159, 64, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    },
                    title: {
                        display: true,
                        text: 'Handelsöversikt'
                    }
                }
            }
        });
    }
    
    // Uppdatera daglig prestanda-diagram
    function updateDailyPerformanceChart(dailyData) {
        const ctx = document.getElementById('daily-performance-chart').getContext('2d');
        
        if (dailyPerformanceChart) {
            dailyPerformanceChart.destroy();
        }
        
        if (!dailyData || dailyData.length === 0) {
            return;
        }
        
        const labels = dailyData.map(d => d.date);
        const buysData = dailyData.map(d => d.buys);
        const sellsData = dailyData.map(d => d.sells);
        const executedData = dailyData.map(d => d.executed);
        const cancelledData = dailyData.map(d => d.cancelled);
        
        dailyPerformanceChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Köp',
                        data: buysData,
                        backgroundColor: 'rgba(54, 162, 235, 0.7)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1,
                        stack: 'Stack 0'
                    },
                    {
                        label: 'Sälj',
                        data: sellsData,
                        backgroundColor: 'rgba(255, 99, 132, 0.7)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1,
                        stack: 'Stack 0'
                    },
                    {
                        label: 'Utförda',
                        data: executedData,
                        backgroundColor: 'rgba(75, 192, 192, 0.7)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1,
                        stack: 'Stack 1'
                    },
                    {
                        label: 'Avbrutna',
                        data: cancelledData,
                        backgroundColor: 'rgba(255, 159, 64, 0.7)',
                        borderColor: 'rgba(255, 159, 64, 1)',
                        borderWidth: 1,
                        stack: 'Stack 1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Datum'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Antal'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Daglig handelsprestanda'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                }
            }
        });
    }
    
    // Uppdatera handelsaktivitet per timme
    function updateHourlyActivityChart(hourlyData) {
        const ctx = document.getElementById('hourly-activity-chart').getContext('2d');
        
        if (hourlyActivityChart) {
            hourlyActivityChart.destroy();
        }
        
        if (!hourlyData || Object.keys(hourlyData).length === 0) {
            return;
        }
        
        // Konvertera objekt till sorterad array
        const hours = Object.keys(hourlyData).sort((a, b) => parseInt(a) - parseInt(b));
        const successRateData = hours.map(hour => {
            // Säkerhetsåtgärd för att hantera saknade attribut
            const hourData = hourlyData[hour] || {};
            const successRate = hourData.success_rate || 0;
            return (successRate * 100).toFixed(1);
        });
        const totalTradesData = hours.map(hour => {
            const hourData = hourlyData[hour] || {};
            return hourData.total || 0;
        });
        
        // Formatera timlabels med ledande nollor
        const hourLabels = hours.map(h => {
            const hour = h.padStart(2, '0');
            return `${hour}:00`;
        });
        
        hourlyActivityChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: hourLabels,
                datasets: [
                    {
                        label: 'Total handelsaktivitet',
                        data: totalTradesData,
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 2,
                        yAxisID: 'y',
                        fill: true
                    },
                    {
                        label: 'Framgångsgrad (%)',
                        data: successRateData,
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 2,
                        yAxisID: 'y1',
                        fill: false,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Timme på dygnet'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Antal trades'
                        },
                        beginAtZero: true
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Framgångsgrad (%)'
                        },
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Handelsaktivitet per timme'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                }
            }
        });
    }
    
    // Uppdatera debug-information
    function updateDebugInfo(data) {
        if (!data) return;
        
        // System stats
        if (data.system_stats) {
            document.getElementById('cpu-usage').textContent = `${data.system_stats.cpu_percent}%`;
            document.getElementById('memory-usage').textContent = `${data.system_stats.memory_percent}%`;
            document.getElementById('disk-usage').textContent = `${data.system_stats.disk_percent}%`;
        }
        
        // Bot status
        if (data.bot_status) {
            document.getElementById('bot-running').textContent = data.bot_status.running ? 'Ja' : 'Nej';
            document.getElementById('bot-pid').textContent = data.bot_status.pid || '-';
            document.getElementById('bot-returncode').textContent = (data.bot_status.returncode !== null) ? 
                data.bot_status.returncode : '-';
        }
        
        // Log files
        if (data.log_files && data.log_files.order_status_log) {
            const log = data.log_files.order_status_log;
            document.getElementById('log-size').textContent = formatBytes(log.size_bytes);
            document.getElementById('log-lines').textContent = log.lines;
            document.getElementById('log-modified').textContent = formatDateTime(new Date(log.last_modified * 1000));
            
            // Visa senaste loggrader
            if (log.last_lines && log.last_lines.length > 0) {
                document.getElementById('log-content').textContent = log.last_lines.join('\n');
            }
        }
    }
    
    // Exportera statistik som CSV
    function exportStatsAsCSV(data) {
        if (!data || !data.trades || data.trades.length === 0) {
            alert('Ingen data tillgänglig för export');
            return;
        }
        
        // Konvertera trades till CSV
        const headers = ['Tid', 'Symbol', 'Typ', 'Pris', 'Mängd', 'Värde', 'Status'];
        
        let csv = headers.join(',') + '\n';
        
        data.trades.forEach(trade => {
            const row = [
                trade.time || '',
                trade.symbol || '',
                trade.side || '',
                trade.price || 0,
                trade.amount || 0,
                trade.value || 0,
                trade.status || ''
            ];
            
            // Escape kommatecken i fälten
            const escapedRow = row.map(field => {
                if (typeof field === 'string' && field.includes(',')) {
                    return `"${field}"`;
                }
                return field;
            });
            
            csv += escapedRow.join(',') + '\n';
        });
        
        // Skapa nedladdningslänk
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        
        const now = new Date();
        const timestamp = now.toISOString().replace(/[:.]/g, '-');
        
        link.setAttribute('href', url);
        link.setAttribute('download', `tradingbot-stats-${timestamp}.csv`);
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    // Registrera händelselyssnare för formuläret
    if (performanceFilterForm) {
        performanceFilterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            fetchStrategyPerformance();
        });
    }
    
    // Lyssnare för detaljnivå-ändringar
    const detailLevelSelect = document.getElementById('detail-level');
    if (detailLevelSelect) {
        detailLevelSelect.addEventListener('change', function() {
            const level = this.value;
            
            // Visa/dölj utökade statistiksektioner baserat på val
            if (level === 'extended' || level === 'full') {
                document.getElementById('extended-stats').style.display = 'block';
            } else {
                document.getElementById('extended-stats').style.display = 'none';
            }
            
            // Visa/dölj debug-sektion endast för full detaljnivå
            if (level === 'full') {
                document.getElementById('debug-section').style.display = 'block';
                // Hämta debug-loggar för full detaljnivå
                fetchDebugLog();
            } else {
                document.getElementById('debug-section').style.display = 'none';
            }
        });
    }
    
    // Lyssnare för export-knappen
    const exportStatsBtn = document.getElementById('export-stats-btn');
    if (exportStatsBtn) {
        exportStatsBtn.addEventListener('click', function() {
            const apiBase = window.location.origin;
            const params = new URLSearchParams();
            params.append('detail_level', 'full'); // Hämta full data för export
            
            // Hämta aktuella filtervärden
            const symbol = document.getElementById('performance-symbol')?.value || '';
            const startDate = document.getElementById('performance-start-date')?.value || '';
            const endDate = document.getElementById('performance-end-date')?.value || '';
            
            if (symbol) params.append('symbol', symbol);
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);
            
            // Hämta data för export
            fetch(`${apiBase}/strategy_performance?${params.toString()}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'ok') {
                        exportStatsAsCSV(data);
                    } else {
                        alert('Kunde inte hämta data för export');
                    }
                })
                .catch(error => {
                    console.error('Fel vid hämtning av exportdata:', error);
                    alert(`Export misslyckades: ${error.message}`);
                });
        });
    }
    
    // Initiera med standardvärden
    function initialize() {
        // Sätt dagens datum som slutdatum som standard
        const today = new Date().toISOString().split('T')[0];
        const endDateInput = document.getElementById('performance-end-date');
        if (endDateInput && !endDateInput.value) {
            endDateInput.value = today;
        }
        
        // Sätt en månad bakåt som startdatum som standard
        const oneMonthAgo = new Date();
        oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);
        const startDateInput = document.getElementById('performance-start-date');
        if (startDateInput && !startDateInput.value) {
            startDateInput.value = oneMonthAgo.toISOString().split('T')[0];
        }
        
        // Ladda initial statistik
        fetchStrategyPerformance();
    }
    
    // Starta initialisering när dokumentet är laddat
    initialize();
});