// Chart.js integration for SPA landing page
// Error handling for Chart.js library loading

// Check if Chart.js is loaded
if (typeof Chart === 'undefined') {
    console.error('Chart.js library failed to load');
    // Display fallback message
    document.addEventListener('DOMContentLoaded', function() {
        const chartContainers = document.querySelectorAll('.chart-container');
        chartContainers.forEach(container => {
            container.innerHTML = '<p class="chart-error">Charts are currently unavailable. Please refresh the page.</p>';
        });
    });
} else {
    // Sample data structures for charts with realistic data
    const chartData = {
        lineChart: {
            labels: ['Jan 2024', 'Feb 2024', 'Mar 2024', 'Apr 2024', 'May 2024', 'Jun 2024', 'Jul 2024', 'Aug 2024', 'Sep 2024', 'Oct 2024', 'Nov 2024', 'Dec 2024'],
            datasets: [{
                label: 'Website Traffic (K visits)',
                data: [45.2, 52.8, 48.1, 61.5, 58.9, 67.3, 72.1, 69.8, 75.4, 81.2, 78.6, 85.3],
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                tension: 0.4,
                fill: true,
                pointBackgroundColor: 'rgb(75, 192, 192)',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 5
            }, {
                label: 'Revenue ($K)',
                data: [125.4, 138.7, 142.3, 156.8, 149.2, 168.5, 175.9, 182.1, 189.7, 195.3, 201.8, 218.4],
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                tension: 0.4,
                fill: true,
                pointBackgroundColor: 'rgb(255, 99, 132)',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 5
            }]
        },
        
        barChart: {
            labels: ['E-commerce Platform', 'Mobile App', 'SaaS Dashboard', 'Marketing Website', 'Analytics Tool', 'CRM System'],
            datasets: [{
                label: 'Q4 2024 Performance Score',
                data: [87.5, 92.3, 78.9, 95.1, 83.7, 89.2],
                backgroundColor: [
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(255, 205, 86, 0.8)',
                    'rgba(153, 102, 255, 0.8)',
                    'rgba(255, 159, 64, 0.8)',
                    'rgba(255, 99, 132, 0.8)'
                ],
                borderColor: [
                    'rgba(54, 162, 235, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 205, 86, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(255, 99, 132, 1)'
                ],
                borderWidth: 2,
                borderRadius: 4,
                borderSkipped: false
            }, {
                label: 'Q3 2024 Performance Score',
                data: [82.1, 88.7, 75.3, 91.8, 79.4, 85.6],
                backgroundColor: [
                    'rgba(54, 162, 235, 0.4)',
                    'rgba(75, 192, 192, 0.4)',
                    'rgba(255, 205, 86, 0.4)',
                    'rgba(153, 102, 255, 0.4)',
                    'rgba(255, 159, 64, 0.4)',
                    'rgba(255, 99, 132, 0.4)'
                ],
                borderColor: [
                    'rgba(54, 162, 235, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 205, 86, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(255, 99, 132, 1)'
                ],
                borderWidth: 2,
                borderRadius: 4,
                borderSkipped: false
            }]
        },
        
        pieChart: {
            labels: ['Direct Traffic', 'Organic Search', 'Social Media', 'Email Marketing', 'Paid Advertising', 'Referrals'],
            datasets: [{
                label: 'Traffic Sources Distribution (%)',
                data: [28.5, 34.2, 15.8, 12.3, 6.7, 2.5],
                backgroundColor: [
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(255, 205, 86, 0.8)',
                    'rgba(153, 102, 255, 0.8)',
                    'rgba(255, 159, 64, 0.8)',
                    'rgba(255, 99, 132, 0.8)'
                ],
                borderColor: [
                    'rgba(54, 162, 235, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 205, 86, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(255, 99, 132, 1)'
                ],
                borderWidth: 3,
                hoverOffset: 10
            }]
        }
    };

    // Chart initialization functions
    function initializeLineChart() {
        try {
            const ctx = document.getElementById('lineChart');
            if (!ctx) {
                console.warn('Line chart canvas element not found');
                return null;
            }
            
            return new Chart(ctx, {
                type: 'line',
                data: chartData.lineChart,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: '2024 Website Traffic & Revenue Trends',
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            padding: 20
                        },
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                usePointStyle: true,
                                padding: 20
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: 'white',
                            bodyColor: 'white',
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Value',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                }
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Month',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                }
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        }
                    },
                    elements: {
                        line: {
                            tension: 0.4
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error initializing line chart:', error);
            displayChartError('lineChart');
            return null;
        }
    }

    function initializeBarChart() {
        try {
            const ctx = document.getElementById('barChart');
            if (!ctx) {
                console.warn('Bar chart canvas element not found');
                return null;
            }
            
            return new Chart(ctx, {
                type: 'bar',
                data: chartData.barChart,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: 'Project Performance Comparison (Q3 vs Q4 2024)',
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            padding: 20
                        },
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                usePointStyle: true,
                                padding: 20
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: 'white',
                            bodyColor: 'white',
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1,
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': ' + context.parsed.y + '/100';
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            title: {
                                display: true,
                                text: 'Performance Score (0-100)',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                }
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            },
                            ticks: {
                                callback: function(value) {
                                    return value + '/100';
                                }
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Projects',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                }
                            },
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            },
                            ticks: {
                                maxRotation: 45,
                                minRotation: 0
                            }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error initializing bar chart:', error);
            displayChartError('barChart');
            return null;
        }
    }

    function initializePieChart() {
        try {
            const ctx = document.getElementById('pieChart');
            if (!ctx) {
                console.warn('Pie chart canvas element not found');
                return null;
            }
            
            return new Chart(ctx, {
                type: 'pie',
                data: chartData.pieChart,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: 'Website Traffic Sources Distribution (2024)',
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            padding: 20
                        },
                        legend: {
                            display: true,
                            position: 'right',
                            labels: {
                                usePointStyle: true,
                                padding: 15,
                                generateLabels: function(chart) {
                                    const data = chart.data;
                                    if (data.labels.length && data.datasets.length) {
                                        return data.labels.map((label, i) => {
                                            const dataset = data.datasets[0];
                                            const value = dataset.data[i];
                                            return {
                                                text: `${label}: ${value}%`,
                                                fillStyle: dataset.backgroundColor[i],
                                                strokeStyle: dataset.borderColor[i],
                                                lineWidth: dataset.borderWidth,
                                                pointStyle: 'circle',
                                                hidden: false,
                                                index: i
                                            };
                                        });
                                    }
                                    return [];
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: 'white',
                            bodyColor: 'white',
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1,
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${label}: ${value}% (${percentage}% of total)`;
                                }
                            }
                        }
                    },
                    animation: {
                        animateRotate: true,
                        animateScale: true
                    }
                }
            });
        } catch (error) {
            console.error('Error initializing pie chart:', error);
            displayChartError('pieChart');
            return null;
        }
    }

    // Error handling helper function
    function displayChartError(chartId) {
        const canvas = document.getElementById(chartId);
        if (canvas && canvas.parentElement) {
            const errorMessage = document.createElement('p');
            errorMessage.className = 'chart-error';
            errorMessage.textContent = 'Unable to load chart. Please refresh the page.';
            canvas.parentElement.appendChild(errorMessage);
            canvas.style.display = 'none';
        }
    }

    // Loading state management
    function setChartLoading(chartId, isLoading) {
        const wrapper = document.getElementById(chartId)?.parentElement;
        if (wrapper) {
            if (isLoading) {
                wrapper.classList.remove('loaded');
            } else {
                wrapper.classList.add('loaded');
            }
        }
    }

    // Initialize all charts when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Initializing charts...');
        
        // Set initial loading state
        ['lineChart', 'barChart', 'pieChart'].forEach(chartId => {
            setChartLoading(chartId, true);
        });
        
        // Add small delay to show loading animation
        setTimeout(() => {
            // Initialize charts with error handling
            const charts = {
                lineChart: initializeLineChart(),
                barChart: initializeBarChart(),
                pieChart: initializePieChart()
            };
            
            // Update loading states and log successful initializations
            Object.keys(charts).forEach(chartName => {
                setChartLoading(chartName, false);
                if (charts[chartName]) {
                    console.log(`${chartName} initialized successfully`);
                }
            });
            
            console.log('Chart initialization complete');
        }, 500); // Small delay to show loading animation
    });
}