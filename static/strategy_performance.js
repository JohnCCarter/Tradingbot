document.addEventListener("DOMContentLoaded", () => {
    // Initialize charts
    const performanceChartCtx = document.getElementById("performanceChart").getContext("2d");
    const dailyProfitChartCtx = document.getElementById("dailyProfitChart").getContext("2d");
    const symbolPerformanceChartCtx = document.getElementById("symbolPerformanceChart").getContext("2d");
    const hourlyDistributionChartCtx = document.getElementById("hourlyDistributionChart").getContext("2d");
    
    // Color scheme
    const colors = {
        primary: "#3498db",
        success: "#2ecc71",
        danger: "#e74c3c",
        warning: "#f39c12",
        info: "#9b59b6"
    };

    // Performance Overview Chart
    const performanceChart = new Chart(performanceChartCtx, {
        type: "line",
        data: {
            labels: [],
            datasets: [
                {
                    label: "Cumulative P&L",
                    data: [],
                    borderColor: colors.primary,
                    backgroundColor: "rgba(52, 152, 219, 0.1)",
                    borderWidth: 2,
                    fill: true,
                    tension: 0.1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `P&L: ${context.raw.toFixed(2)}`;
                        }
                    }
                },
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Strategy Performance Over Time',
                    font: {
                        size: 16
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: "Date",
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: "Profit/Loss",
                    },
                    grid: {
                        color: "rgba(0, 0, 0, 0.05)"
                    }
                },
            },
        },
    });
    
    // Daily Profit Chart
    const dailyProfitChart = new Chart(dailyProfitChartCtx, {
        type: "bar",
        data: {
            labels: [],
            datasets: [
                {
                    label: "Daily P&L",
                    data: [],
                    backgroundColor: [],
                    borderColor: [],
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `P&L: ${context.raw.toFixed(2)}`;
                        }
                    }
                },
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Daily Profit/Loss',
                    font: {
                        size: 16
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: "Date"
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: "Profit/Loss"
                    },
                    grid: {
                        color: "rgba(0, 0, 0, 0.05)"
                    }
                }
            }
        }
    });
    
    // Symbol Performance Chart
    const symbolPerformanceChart = new Chart(symbolPerformanceChartCtx, {
        type: "doughnut",
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(153, 102, 255, 0.7)',
                    'rgba(255, 159, 64, 0.7)',
                    'rgba(199, 199, 199, 0.7)',
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(199, 199, 199, 1)',
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                },
                title: {
                    display: true,
                    text: 'Performance by Symbol',
                    font: {
                        size: 16
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const symbol = context.label;
                            const value = context.raw.toFixed(2);
                            return `${symbol}: ${value}`;
                        }
                    }
                }
            }
        }
    });
    
    // Hourly Distribution Chart
    const hourlyDistributionChart = new Chart(hourlyDistributionChartCtx, {
        type: "bar",
        data: {
            labels: Array.from({ length: 24 }, (_, i) => i),
            datasets: [{
                label: 'Trade Count',
                data: Array(24).fill(0),
                backgroundColor: 'rgba(54, 162, 235, 0.7)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: 'Hourly Trading Activity',
                    font: {
                        size: 16
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: "Hour"
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: "Number of Trades"
                    },
                    grid: {
                        color: "rgba(0, 0, 0, 0.05)"
                    }
                }
            }
        }
    });
    
    // Format currency values
    function formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
        }).format(value);
    }
    
    // Format percentage values
    function formatPercent(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'percent',
            minimumFractionDigits: 2
        }).format(value/100);
    }

    async function fetchPerformanceData() {
        try {
            // Get filter values
            const symbol = document.getElementById('performance-symbol')?.value || '';
            const startDate = document.getElementById('performance-start-date')?.value || '';
            const endDate = document.getElementById('performance-end-date')?.value || '';
            
            // Build API URL
            const apiBase = window.location.origin;
            const params = new URLSearchParams();
            if (symbol) params.append('symbol', symbol);
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);
            
            const url = `${apiBase}/strategy_performance?${params.toString()}`;
            
            // Show loading indicator
            document.getElementById('performance-loading').style.display = 'block';
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            // Hide loading indicator
            document.getElementById('performance-loading').style.display = 'none';
            
            if (!data || data.error) {
                console.error("Error in performance data:", data?.error || "No data returned");
                document.getElementById('performance-error').textContent = data?.error || "Failed to load performance data";
                document.getElementById('performance-error').style.display = 'block';
                return;
            }
            
            // Hide error message if present
            document.getElementById('performance-error').style.display = 'none';
            
            // Update overview metrics
            updatePerformanceMetrics(data.metrics);
            
            // Update charts
            updatePerformanceChart(data.metrics);
            updateDailyProfitChart(data.metrics);
            updateSymbolPerformanceChart(data.metrics);
            updateHourlyDistributionChart(data.metrics);
            
            // Update tables
            if (data.trades && data.trades.length > 0) {
                updateTradesTable(data.trades);
            }
            
            // Log data for debugging
            console.log("Performance data:", data);
            
        } catch (error) {
            console.error("Error fetching performance data:", error);
            document.getElementById('performance-error').textContent = `Error: ${error.message}`;
            document.getElementById('performance-error').style.display = 'block';
            document.getElementById('performance-loading').style.display = 'none';
        }
    }
    
    // Update performance metrics
    function updatePerformanceMetrics(metrics) {
        // Basic metrics
        document.getElementById('total-trades').textContent = metrics.total_trades || 0;
        document.getElementById('total-buys').textContent = metrics.buy_trades || 0;
        document.getElementById('total-sells').textContent = metrics.sell_trades || 0;
        document.getElementById('total-executed').textContent = metrics.executed_trades || 0;
        document.getElementById('total-cancelled').textContent = metrics.cancelled_trades || 0;
        
        // P&L metrics
        const profitLoss = document.getElementById('profit-loss');
        profitLoss.textContent = formatCurrency(metrics.profit_loss || 0);
        profitLoss.className = (metrics.profit_loss || 0) >= 0 ? 'positive' : 'negative';
        
        const avgProfit = document.getElementById('avg-profit');
        avgProfit.textContent = formatCurrency(metrics.avg_profit_per_trade || 0);
        avgProfit.className = (metrics.avg_profit_per_trade || 0) >= 0 ? 'positive' : 'negative';
        
        // Performance metrics
        document.getElementById('win-rate').textContent = 
            `${(metrics.win_rate || 0).toFixed(2)}%`;
        document.getElementById('risk-reward-ratio').textContent = 
            (metrics.risk_reward_ratio || 0).toFixed(2);
        
        // Additional metrics
        document.getElementById('max-win-streak').textContent = 
            metrics.max_consecutive_wins || 0;
        document.getElementById('max-loss-streak').textContent = 
            metrics.max_consecutive_losses || 0;
        
        // Largest profit/loss
        const largestProfit = document.getElementById('largest-profit');
        largestProfit.textContent = formatCurrency(metrics.largest_profit || 0);
        largestProfit.className = 'positive';
        
        const largestLoss = document.getElementById('largest-loss');
        largestLoss.textContent = formatCurrency(metrics.largest_loss || 0);
        largestLoss.className = 'negative';
    }
    
    // Update performance chart
    function updatePerformanceChart(metrics) {
        if (!metrics.daily_performance || metrics.daily_performance.length === 0) {
            return;
        }
        
        // Sort by date
        const dailyData = [...metrics.daily_performance].sort((a, b) => 
            new Date(a.date) - new Date(b.date)
        );
        
        // Calculate cumulative P&L
        let cumulativePL = 0;
        const chartData = dailyData.map(day => {
            cumulativePL += (day.profit_loss || 0);
            return {
                x: new Date(day.date).toISOString().split('T')[0],
                y: cumulativePL
            };
        });
        
        // Update chart
        performanceChart.data.labels = chartData.map(d => d.x);
        performanceChart.data.datasets[0].data = chartData;
        performanceChart.update();
    }
    
    // Update daily profit chart
    function updateDailyProfitChart(metrics) {
        if (!metrics.daily_performance || metrics.daily_performance.length === 0) {
            return;
        }
        
        // Sort by date
        const dailyData = [...metrics.daily_performance].sort((a, b) => 
            new Date(a.date) - new Date(b.date)
        );
        
        // Prepare chart data
        const labels = dailyData.map(day => day.date);
        const values = dailyData.map(day => day.profit_loss || 0);
        
        // Set colors based on profit/loss
        const backgroundColors = values.map(val => 
            val >= 0 ? 'rgba(46, 204, 113, 0.6)' : 'rgba(231, 76, 60, 0.6)'
        );
        const borderColors = values.map(val => 
            val >= 0 ? 'rgba(46, 204, 113, 1)' : 'rgba(231, 76, 60, 1)'
        );
        
        // Update chart
        dailyProfitChart.data.labels = labels;
        dailyProfitChart.data.datasets[0].data = values;
        dailyProfitChart.data.datasets[0].backgroundColor = backgroundColors;
        dailyProfitChart.data.datasets[0].borderColor = borderColors;
        dailyProfitChart.update();
    }
    
    // Update symbol performance chart
    function updateSymbolPerformanceChart(metrics) {
        if (!metrics.symbol_performance || metrics.symbol_performance.length === 0) {
            return;
        }
        
        // Sort by profit/loss
        const symbolData = [...metrics.symbol_performance].sort((a, b) => 
            (b.profit_loss || 0) - (a.profit_loss || 0)
        );
        
        // Prepare chart data
        const labels = symbolData.map(item => item.symbol);
        const values = symbolData.map(item => item.profit_loss || 0);
        
        // Update chart
        symbolPerformanceChart.data.labels = labels;
        symbolPerformanceChart.data.datasets[0].data = values;
        symbolPerformanceChart.update();
    }
    
    // Update hourly distribution chart
    function updateHourlyDistributionChart(metrics) {
        if (!metrics.hourly_distribution || metrics.hourly_distribution.length === 0) {
            return;
        }
        
        // Initialize data array with zeros for all 24 hours
        const hourData = Array(24).fill(0);
        
        // Fill in data from metrics
        metrics.hourly_distribution.forEach(item => {
            const hour = parseInt(item.hour);
            if (hour >= 0 && hour < 24) {
                hourData[hour] = item.count;
            }
        });
        
        // Update chart
        hourlyDistributionChart.data.datasets[0].data = hourData;
        hourlyDistributionChart.update();
    }
    
    // Update trades table
    function updateTradesTable(trades) {
        const table = document.getElementById('performance-trades-table');
        table.innerHTML = '';
        
        if (trades.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="7">No trades found</td>';
            table.appendChild(row);
            return;
        }
        
        // Sort trades by time (newest first)
        const sortedTrades = [...trades].sort((a, b) => 
            new Date(b.time) - new Date(a.time)
        );
        
        // Show only the most recent 20 trades
        sortedTrades.slice(0, 20).forEach(trade => {
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
            
            // Format time to show only time portion if date is today
            let timeDisplay = trade.time;
            if (timeDisplay && timeDisplay.includes(' ')) {
                const parts = timeDisplay.split(' ');
                const today = new Date().toISOString().split('T')[0];
                if (parts[0] === today) {
                    timeDisplay = parts[1];
                }
            }
            
            row.innerHTML = `
                <td>${timeDisplay || '-'}</td>
                <td>${trade.symbol || '-'}</td>
                <td class="${trade.side === 'buy' ? 'buy-side' : 'sell-side'}">${trade.side || '-'}</td>
                <td>${formatCurrency(trade.price || 0)}</td>
                <td>${trade.amount || '-'}</td>
                <td>${formatCurrency(trade.value || 0)}</td>
                <td class="${statusClass}">${trade.status || '-'}</td>
            `;
            
            table.appendChild(row);
        });
    }
    
    // Export data as CSV
    window.exportPerformanceData = function() {
        try {
            // Get current filter values
            const symbol = document.getElementById('performance-symbol')?.value || '';
            const startDate = document.getElementById('performance-start-date')?.value || '';
            const endDate = document.getElementById('performance-end-date')?.value || '';
            
            // Build API URL
            const apiBase = window.location.origin;
            const params = new URLSearchParams();
            if (symbol) params.append('symbol', symbol);
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);
            params.append('format', 'csv');  // Request CSV format
            
            const url = `${apiBase}/strategy_performance?${params.toString()}`;
            
            // Trigger download
            window.location.href = url;
            
        } catch (error) {
            console.error("Error exporting data:", error);
            alert("Failed to export data: " + error.message);
        }
    };
    
    // Set up filter event handlers
    document.getElementById('performance-filter-form').addEventListener('submit', function(e) {
        e.preventDefault();
        fetchPerformanceData();
    });
    
    // Initialize with a data fetch
    fetchPerformanceData();
    
    // Refresh data periodically (every 30 seconds)
    setInterval(fetchPerformanceData, 30000);
});