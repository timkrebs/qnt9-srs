/**
 * QNT9 Stock Chart - Professional Interactive Chart Component
 * Uses Chart.js with zoom, pan, crosshair, and multiple timeframes
 */

class StockChart {
    constructor(canvasId, stockSymbol, currentPrice) {
        this.canvasId = canvasId;
        this.stockSymbol = stockSymbol || 'DEMO';
        this.currentPrice = currentPrice || 100;
        this.chart = null;
        this.currentPeriod = '1D';
        this.chartType = 'line';
    }
    
    // Get responsive configuration based on screen size
    getResponsiveConfig() {
        const isMobile = window.innerWidth < 640;
        return {
            fontSize: {
                tick: isMobile ? 10 : 12,
                tooltipTitle: isMobile ? 12 : 14,
                tooltipBody: isMobile ? 11 : 13
            },
            maxTicks: {
                x: isMobile ? 4 : 8,
                y: isMobile ? 5 : 8
            },
            tooltipPadding: isMobile ? 8 : 12,
            isMobile: isMobile
        };
    }
    
    // Fetch real historical data from backend
    async fetchHistoricalData(period) {
        try {
            // Map frontend periods to backend periods and intervals
            const periodMapping = {
                '1D': { period: '1d', interval: '5m' },
                '5D': { period: '5d', interval: '15m' },
                '1M': { period: '1mo', interval: '1d' },
                '3M': { period: '3mo', interval: '1d' },
                '1Y': { period: '1y', interval: '1d' },
                '5Y': { period: '5y', interval: '1wk' }
            };

            const mapping = periodMapping[period] || { period: '1d', interval: '5m' };
            
            const response = await fetch(
                `/api/historical/${this.stockSymbol}?period=${mapping.period}&interval=${mapping.interval}`
            );
            
            if (!response.ok) {
                console.warn(`Failed to fetch historical data: ${response.status}`);
                return this.generateMockData(period);
            }
            
            const result = await response.json();
            
            if (result.success && result.data && result.data.length > 0) {
                console.log(`Fetched ${result.count} real data points for ${this.stockSymbol} (${period})`);
                return this.processHistoricalData(result.data);
            } else {
                console.warn('No historical data available, using mock data');
                return this.generateMockData(period);
            }
            
        } catch (error) {
            console.error('Error fetching historical data:', error);
            return this.generateMockData(period);
        }
    }

    // Process real historical data from backend
    processHistoricalData(historicalData) {
        const data = [];
        
        for (const point of historicalData) {
            const date = new Date(point.timestamp);
            
            // Use real OHLCV data if available, otherwise use close price
            data.push({
                x: date,
                o: parseFloat(point.open || point.close),
                h: parseFloat(point.high || point.close),
                l: parseFloat(point.low || point.close),
                c: parseFloat(point.close),
                volume: point.volume || 0
            });
        }
        
        return data;
    }

    // Generate realistic mock data for demonstration (fallback)
    generateMockData(period) {
        const now = new Date();
        const data = [];
        let intervals, startDate, intervalMs;
        
        switch(period) {
            case '1D':
                intervals = 78; // 5-minute intervals for 6.5 hours
                intervalMs = 5 * 60 * 1000;
                startDate = new Date(now.getTime() - (6.5 * 60 * 60 * 1000));
                break;
            case '5D':
                intervals = 390; // 5-minute intervals for 5 days
                intervalMs = 5 * 60 * 1000;
                startDate = new Date(now.getTime() - (5 * 24 * 60 * 60 * 1000));
                break;
            case '1M':
                intervals = 30;
                intervalMs = 24 * 60 * 60 * 1000;
                startDate = new Date(now.getTime() - (30 * 24 * 60 * 60 * 1000));
                break;
            case '3M':
                intervals = 90;
                intervalMs = 24 * 60 * 60 * 1000;
                startDate = new Date(now.getTime() - (90 * 24 * 60 * 60 * 1000));
                break;
            case '1Y':
                intervals = 365;
                intervalMs = 24 * 60 * 60 * 1000;
                startDate = new Date(now.getTime() - (365 * 24 * 60 * 60 * 1000));
                break;
            case '5Y':
                intervals = 1825;
                intervalMs = 24 * 60 * 60 * 1000;
                startDate = new Date(now.getTime() - (5 * 365 * 24 * 60 * 60 * 1000));
                break;
        }
        
        let price = this.currentPrice;
        const volatility = 0.02;
        
        for (let i = 0; i < intervals; i++) {
            const date = new Date(startDate.getTime() + (i * intervalMs));
            
            // Generate realistic OHLC data
            const change = (Math.random() - 0.5) * volatility * price;
            const open = price;
            const close = price + change;
            const high = Math.max(open, close) + (Math.random() * 0.01 * price);
            const low = Math.min(open, close) - (Math.random() * 0.01 * price);
            
            data.push({
                x: date,
                o: parseFloat(open.toFixed(2)),
                h: parseFloat(high.toFixed(2)),
                l: parseFloat(low.toFixed(2)),
                c: parseFloat(close.toFixed(2))
            });
            
            price = close;
        }
        
        return data;
    }
    
    // Chart configuration
    getChartConfig(data) {
        const isPositive = data.length > 0 && data[data.length - 1].c > data[0].o;
        
        if (this.chartType === 'candlestick') {
            return this.getCandlestickConfig(data, isPositive);
        } else {
            return this.getLineConfig(data, isPositive);
        }
    }
    
    // Line chart configuration
    getLineConfig(data, isPositive) {
        const responsive = this.getResponsiveConfig();
        
        return {
            type: 'line',
            data: {
                datasets: [{
                    label: this.stockSymbol + ' Price',
                    data: data.map(d => ({x: d.x, y: d.c})),
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: responsive.isMobile ? 1.5 : 2,
                    fill: true,
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    pointHoverBackgroundColor: 'transparent',
                    pointHoverBorderColor: 'transparent',
                    pointHoverBorderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#374151',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: false,
                        titleFont: {
                            size: responsive.fontSize.tooltipTitle
                        },
                        bodyFont: {
                            size: responsive.fontSize.tooltipBody
                        },
                        padding: responsive.tooltipPadding,
                        callbacks: {
                            title: function(context) {
                                const date = new Date(context[0].parsed.x);
                                if (responsive.isMobile) {
                                    return date.toLocaleDateString();
                                }
                                return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                            },
                            label: function(context) {
                                return `Price: €${context.parsed.y.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                minute: 'HH:mm',
                                hour: 'HH:mm',
                                day: 'MMM dd',
                                month: 'MMM yyyy'
                            }
                        },
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#6b7280',
                            font: {
                                size: 12
                            }
                        }
                    },
                    y: {
                        position: 'right',
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#6b7280',
                            font: {
                                size: 12
                            },
                            callback: function(value) {
                                return '€' + value.toFixed(2);
                            }
                        }
                    }
                },
                animation: {
                    duration: 750,
                    easing: 'easeInOutQuart'
                }
            },
            plugins: []
        };
    }
    
    // Candlestick chart configuration (simplified OHLC line chart)
    getCandlestickConfig(data, isPositive) {
        // Create datasets for OHLC visualization
        const openData = data.map(d => ({x: d.x, y: d.o}));
        const highData = data.map(d => ({x: d.x, y: d.h}));
        const lowData = data.map(d => ({x: d.x, y: d.l}));
        const closeData = data.map(d => ({x: d.x, y: d.c}));
        
        return {
            type: 'line',
            data: {
                datasets: [
                    // High line (thin gray)
                    {
                        label: 'High',
                        data: highData,
                        borderColor: '#9ca3af',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        fill: false,
                        tension: 0,
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        order: 4
                    },
                    // Low line (thin gray)
                    {
                        label: 'Low',
                        data: lowData,
                        borderColor: '#9ca3af',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        fill: false,
                        tension: 0,
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        order: 3
                    },
                    // Open line (green)
                    {
                        label: 'Open',
                        data: openData,
                        borderColor: '#10b981',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        fill: false,
                        tension: 0,
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        borderDash: [5, 5],
                        order: 2
                    },
                    // Close line (main line - thicker)
                    {
                        label: this.stockSymbol + ' Close Price',
                        data: closeData,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 3,
                        fill: false,
                        tension: 0.1,
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        order: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#374151',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: false,
                        filter: function(tooltipItem) {
                            // Only show tooltip for the main Close line (dataset index 3)
                            return tooltipItem.datasetIndex === 3;
                        },
                        callbacks: {
                            title: function(context) {
                                const date = new Date(context[0].parsed.x);
                                return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                            },
                            label: function(context) {
                                // Find the corresponding OHLC data point
                                const index = context.dataIndex;
                                if (index < data.length) {
                                    const point = data[index];
                                    return [
                                        `Open: €${point.o.toFixed(2)}`,
                                        `High: €${point.h.toFixed(2)}`,
                                        `Low: €${point.l.toFixed(2)}`,
                                        `Close: €${point.c.toFixed(2)}`
                                    ];
                                }
                                return null;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                minute: 'HH:mm',
                                hour: 'HH:mm',
                                day: 'MMM dd',
                                month: 'MMM yyyy'
                            }
                        },
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#6b7280',
                            font: {
                                size: 12
                            }
                        }
                    },
                    y: {
                        position: 'right',
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#6b7280',
                            font: {
                                size: 12
                            },
                            callback: function(value) {
                                return '€' + value.toFixed(2);
                            }
                        }
                    }
                },
                animation: {
                    duration: 750,
                    easing: 'easeInOutQuart'
                }
            },
            plugins: []
        };
    }
    
    // Initialize chart
    async init() {
        const canvas = document.getElementById(this.canvasId);
        if (!canvas) {
            console.error(`Canvas element not found: ${this.canvasId}`);
            return;
        }
        
        if (!window.Chart) {
            console.error('Chart.js not loaded');
            return;
        }
        
        try {
            const ctx = canvas.getContext('2d');
            console.log(`Fetching data for ${this.stockSymbol}...`);
            const data = await this.fetchHistoricalData(this.currentPeriod);
            
            if (!data || data.length === 0) {
                console.warn('No data received, using mock data');
                const mockData = this.generateMockData(this.currentPeriod);
                this.createChart(ctx, mockData);
            } else {
                console.log(`Received ${data.length} data points`);
                this.createChart(ctx, data);
            }
            
            this.updateLastUpdateTime();
        } catch (error) {
            console.error('Error in chart initialization:', error);
            throw error;
        }
    }
    
    createChart(ctx, data) {
        if (this.chart) {
            this.chart.destroy();
        }
        
        this.chart = new Chart(ctx, this.getChartConfig(data));
    }
    
    // Update chart data
    async updateChart(period) {
        if (!this.chart) return;
        
        this.currentPeriod = period;
        
        // Show loading
        this.showLoading();
        
        try {
            const data = await this.fetchHistoricalData(period);
            
            // Destroy and recreate chart with new data
            const ctx = this.chart.ctx;
            this.chart.destroy();
            this.createChart(ctx, data);
            
            // Hide loading
            this.hideLoading();
            this.updateLastUpdateTime();
        } catch (error) {
            console.error('Error updating chart:', error);
            this.hideLoading();
        }
    }
    
    // Toggle chart type
    toggleChartType() {
        this.chartType = this.chartType === 'line' ? 'candlestick' : 'line';
        this.updateChart(this.currentPeriod);
        return this.chartType;
    }
    
    // Reset zoom
    resetZoom() {
        if (this.chart) {
            this.chart.resetZoom();
        }
    }
    
    // Resize chart
    resize() {
        if (this.chart) {
            this.chart.resize();
        }
    }
    
    // Destroy chart
    destroy() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }
    
    // Helper methods
    showLoading() {
        const loading = document.getElementById('chart-loading');
        if (loading) loading.classList.remove('hidden');
    }
    
    hideLoading() {
        const loading = document.getElementById('chart-loading');
        if (loading) loading.classList.add('hidden');
    }
    
    updateLastUpdateTime() {
        const updateElement = document.getElementById('chart-last-update');
        if (updateElement) {
            updateElement.textContent = new Date().toLocaleTimeString();
        }
    }
}

// Export for use in templates
window.StockChart = StockChart;
