document.addEventListener("DOMContentLoaded", () => {
    const ctx = document.getElementById("performanceChart").getContext("2d");

    const performanceChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: [],
            datasets: [
                {
                    label: "Strategy Performance",
                    data: [],
                    borderColor: "#3498db",
                    borderWidth: 2,
                    fill: false,
                },
            ],
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: "Time",
                    },
                },
                y: {
                    title: {
                        display: true,
                        text: "Performance",
                    },
                },
            },
        },
    });

    async function fetchPerformanceData() {
        try {
            const response = await fetch("http://127.0.0.1:5000/performance");
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            // Update chart data
            performanceChart.data.labels = data.timestamps;
            performanceChart.data.datasets[0].data = data.values;
            performanceChart.update();
        } catch (error) {
            console.error("Error fetching performance data:", error);
        }
    }

    // Fetch data every 5 seconds
    setInterval(fetchPerformanceData, 5000);
    fetchPerformanceData();
});