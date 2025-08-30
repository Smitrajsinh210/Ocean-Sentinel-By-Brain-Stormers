/**
 * Ocean Sentinel - D3.js Chart Components
 * Advanced data visualizations for environmental and threat data
 */

class ThreatTimeline {
    constructor(containerId) {
        this.container = d3.select(containerId);
        this.margin = { top: 20, right: 30, bottom: 40, left: 50 };
        this.width = 800 - this.margin.left - this.margin.right;
        this.height = 400 - this.margin.top - this.margin.bottom;
        
        this.svg = null;
        this.xScale = null;
        this.yScale = null;
        this.line = null;
        this.data = [];
        
        this.init();
    }
    
    init() {
        // Create SVG
        this.svg = this.container
            .append('svg')
            .attr('width', this.width + this.margin.left + this.margin.right)
            .attr('height', this.height + this.margin.top + this.margin.bottom)
            .append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);
        
        // Create scales
        this.xScale = d3.scaleTime().range([0, this.width]);
        this.yScale = d3.scaleLinear().range([this.height, 0]);
        
        // Create line generator
        this.line = d3.line()
            .x(d => this.xScale(new Date(d.timestamp)))
            .y(d => this.yScale(d.severity))
            .curve(d3.curveMonotoneX);
        
        // Add axes
        this.svg.append('g')
            .attr('class', 'x-axis')
            .attr('transform', `translate(0,${this.height})`);
        
        this.svg.append('g')
            .attr('class', 'y-axis');
        
        // Add axis labels
        this.svg.append('text')
            .attr('class', 'axis-label')
            .attr('transform', 'rotate(-90)')
            .attr('y', 0 - this.margin.left)
            .attr('x', 0 - (this.height / 2))
            .attr('dy', '1em')
            .style('text-anchor', 'middle')
            .text('Threat Severity');
        
        this.svg.append('text')
            .attr('class', 'axis-label')
            .attr('transform', `translate(${this.width / 2}, ${this.height + this.margin.bottom})`)
            .style('text-anchor', 'middle')
            .text('Time');
    }
    
    updateData(newData) {
        this.data = newData.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        this.render();
    }
    
    render() {
        if (this.data.length === 0) return;
        
        // Update scales
        this.xScale.domain(d3.extent(this.data, d => new Date(d.timestamp)));
        this.yScale.domain([0, d3.max(this.data, d => d.severity)]);
        
        // Update axes
        this.svg.select('.x-axis')
            .transition()
            .duration(750)
            .call(d3.axisBottom(this.xScale).tickFormat(d3.timeFormat('%H:%M')));
        
        this.svg.select('.y-axis')
            .transition()
            .duration(750)
            .call(d3.axisLeft(this.yScale));
        
        // Group data by threat type
        const groupedData = d3.group(this.data, d => d.type);
        
        // Color scale for threat types
        const colorScale = d3.scaleOrdinal()
            .domain(['storm', 'pollution', 'erosion', 'algal_bloom', 'illegal_dumping'])
            .range(['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7']);
        
        // Draw lines for each threat type
        groupedData.forEach((values, key) => {
            const pathId = `line-${key}`;
            
            let path = this.svg.select(`#${pathId}`);
            if (path.empty()) {
                path = this.svg.append('path')
                    .attr('id', pathId)
                    .attr('class', 'threat-line')
                    .attr('fill', 'none')
                    .attr('stroke', colorScale(key))
                    .attr('stroke-width', 2);
            }
            
            path.datum(values)
                .transition()
                .duration(750)
                .attr('d', this.line);
        });
        
        // Add dots for individual threats
        const circles = this.svg.selectAll('.threat-dot')
            .data(this.data, d => d.id);
        
        circles.exit().remove();
        
        circles.enter()
            .append('circle')
            .attr('class', 'threat-dot')
            .attr('r', 0)
            .merge(circles)
            .transition()
            .duration(750)
            .attr('cx', d => this.xScale(new Date(d.timestamp)))
            .attr('cy', d => this.yScale(d.severity))
            .attr('r', d => 3 + d.confidence * 2)
            .attr('fill', d => colorScale(d.type))
            .attr('opacity', 0.8);
        
        // Add tooltips
        this.addTooltips();
    }
    
    addTooltips() {
        const tooltip = d3.select('body').selectAll('.timeline-tooltip')
            .data([0])
            .enter()
            .append('div')
            .attr('class', 'timeline-tooltip')
            .style('opacity', 0)
            .style('position', 'absolute')
            .style('background', 'rgba(0, 0, 0, 0.8)')
            .style('color', 'white')
            .style('padding', '10px')
            .style('border-radius', '5px')
            .style('pointer-events', 'none');
        
        this.svg.selectAll('.threat-dot')
            .on('mouseover', (event, d) => {
                tooltip.transition().duration(200).style('opacity', .9);
                tooltip.html(`
                    <strong>${d.type.charAt(0).toUpperCase() + d.type.slice(1)} Threat</strong><br/>
                    Severity: ${d.severity}/5<br/>
                    Confidence: ${Math.round(d.confidence * 100)}%<br/>
                    Time: ${new Date(d.timestamp).toLocaleString()}
                `)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 28) + 'px');
            })
            .on('mouseout', () => {
                tooltip.transition().duration(500).style('opacity', 0);
            });
    }
}

class SeverityChart {
    constructor(containerId) {
        this.container = d3.select(containerId);
        this.margin = { top: 20, right: 20, bottom: 30, left: 40 };
        this.width = 400 - this.margin.left - this.margin.right;
        this.height = 300 - this.margin.top - this.margin.bottom;
        
        this.svg = null;
        this.data = [];
        
        this.init();
    }
    
    init() {
        this.svg = this.container
            .append('svg')
            .attr('width', this.width + this.margin.left + this.margin.right)
            .attr('height', this.height + this.margin.top + this.margin.bottom)
            .append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);
        
        // Add title
        this.svg.append('text')
            .attr('class', 'chart-title')
            .attr('x', this.width / 2)
            .attr('y', 0 - (this.margin.top / 2))
            .attr('text-anchor', 'middle')
            .style('font-size', '16px')
            .style('font-weight', 'bold')
            .text('Threat Severity Distribution');
    }
    
    updateData(threats) {
        // Count threats by severity
        const severityCount = d3.rollup(
            threats, 
            v => v.length, 
            d => d.severity
        );
        
        this.data = Array.from({length: 5}, (_, i) => ({
            severity: i + 1,
            count: severityCount.get(i + 1) || 0,
            label: ['Minor', 'Moderate', 'Significant', 'Dangerous', 'Extreme'][i]
        }));
        
        this.render();
    }
    
    render() {
        // Create scales
        const xScale = d3.scaleBand()
            .domain(this.data.map(d => d.severity))
            .range([0, this.width])
            .padding(0.1);
        
        const yScale = d3.scaleLinear()
            .domain([0, d3.max(this.data, d => d.count) || 1])
            .range([this.height, 0]);
        
        // Color scale based on severity
        const colorScale = d3.scaleSequential()
            .domain([1, 5])
            .interpolator(d3.interpolateReds);
        
        // Bind data to bars
        const bars = this.svg.selectAll('.severity-bar')
            .data(this.data);
        
        bars.exit().remove();
        
        bars.enter()
            .append('rect')
            .attr('class', 'severity-bar')
            .attr('x', d => xScale(d.severity))
            .attr('width', xScale.bandwidth())
            .attr('y', this.height)
            .attr('height', 0)
            .merge(bars)
            .transition()
            .duration(750)
            .attr('y', d => yScale(d.count))
            .attr('height', d => this.height - yScale(d.count))
            .attr('fill', d => colorScale(d.severity));
        
        // Add axes
        this.svg.selectAll('.x-axis').remove();
        this.svg.selectAll('.y-axis').remove();
        
        this.svg.append('g')
            .attr('class', 'x-axis')
            .attr('transform', `translate(0,${this.height})`)
            .call(d3.axisBottom(xScale).tickFormat((d, i) => this.data[i].label));
        
        this.svg.append('g')
            .attr('class', 'y-axis')
            .call(d3.axisLeft(yScale));
        
        // Add value labels on bars
        const labels = this.svg.selectAll('.bar-label')
            .data(this.data);
        
        labels.exit().remove();
        
        labels.enter()
            .append('text')
            .attr('class', 'bar-label')
            .merge(labels)
            .transition()
            .duration(750)
            .attr('x', d => xScale(d.severity) + xScale.bandwidth() / 2)
            .attr('y', d => yScale(d.count) - 5)
            .attr('text-anchor', 'middle')
            .style('font-size', '12px')
            .style('fill', '#333')
            .text(d => d.count > 0 ? d.count : '');
    }
}

class EnvironmentalChart {
    constructor(containerId) {
        this.container = d3.select(containerId);
        this.margin = { top: 20, right: 80, bottom: 30, left: 50 };
        this.width = 600 - this.margin.left - this.margin.right;
        this.height = 300 - this.margin.top - this.margin.bottom;
        
        this.svg = null;
        this.data = [];
        
        this.init();
    }
    
    init() {
        this.svg = this.container
            .append('svg')
            .attr('width', this.width + this.margin.left + this.margin.right)
            .attr('height', this.height + this.margin.top + this.margin.bottom)
            .append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);
    }
    
    updateData(environmentalData) {
        if (!environmentalData) return;
        
        // Transform data for visualization
        this.data = this.prepareEnvironmentalData(environmentalData);
        this.render();
    }
    
    prepareEnvironmentalData(data) {
        const metrics = [];
        
        // Extract various environmental metrics
        if (data.weather) {
            metrics.push({
                name: 'Temperature',
                value: data.weather.temperature,
                unit: '°C',
                category: 'weather'
            });
            metrics.push({
                name: 'Humidity',
                value: data.weather.humidity,
                unit: '%',
                category: 'weather'
            });
            metrics.push({
                name: 'Wind Speed',
                value: data.weather.wind_speed,
                unit: 'm/s',
                category: 'weather'
            });
        }
        
        if (data.air_quality) {
            metrics.push({
                name: 'PM2.5',
                value: data.air_quality.pm2_5,
                unit: 'µg/m³',
                category: 'air_quality'
            });
            metrics.push({
                name: 'AQI',
                value: data.air_quality.aqi,
                unit: '',
                category: 'air_quality'
            });
        }
        
        if (data.ocean) {
            metrics.push({
                name: 'Water Level',
                value: data.ocean.water_level,
                unit: 'm',
                category: 'ocean'
            });
            metrics.push({
                name: 'Wave Height',
                value: data.ocean.wave_height,
                unit: 'm',
                category: 'ocean'
            });
        }
        
        return metrics;
    }
    
    render() {
        if (this.data.length === 0) return;
        
        // Clear previous content
        this.svg.selectAll('*').remove();
        
        // Create scales
        const xScale = d3.scaleBand()
            .domain(this.data.map(d => d.name))
            .range([0, this.width])
            .padding(0.1);
        
        const yScale = d3.scaleLinear()
            .domain([0, d3.max(this.data, d => d.value) * 1.1])
            .range([this.height, 0]);
        
        // Color scale by category
        const colorScale = d3.scaleOrdinal()
            .domain(['weather', 'air_quality', 'ocean'])
            .range(['#3498db', '#e74c3c', '#2ecc71']);
        
        // Create bars
        this.svg.selectAll('.env-bar')
            .data(this.data)
            .enter()
            .append('rect')
            .attr('class', 'env-bar')
            .attr('x', d => xScale(d.name))
            .attr('width', xScale.bandwidth())
            .attr('y', this.height)
            .attr('height', 0)
            .attr('fill', d => colorScale(d.category))
            .transition()
            .duration(750)
            .attr('y', d => yScale(d.value))
            .attr('height', d => this.height - yScale(d.value));
        
        // Add axes
        this.svg.append('g')
            .attr('class', 'x-axis')
            .attr('transform', `translate(0,${this.height})`)
            .call(d3.axisBottom(xScale))
            .selectAll('text')
            .style('text-anchor', 'end')
            .attr('dx', '-.8em')
            .attr('dy', '.15em')
            .attr('transform', 'rotate(-45)');
        
        this.svg.append('g')
            .attr('class', 'y-axis')
            .call(d3.axisLeft(yScale));
        
        // Add value labels
        this.svg.selectAll('.env-label')
            .data(this.data)
            .enter()
            .append('text')
            .attr('class', 'env-label')
            .attr('x', d => xScale(d.name) + xScale.bandwidth() / 2)
            .attr('y', d => yScale(d.value) - 5)
            .attr('text-anchor', 'middle')
            .style('font-size', '10px')
            .text(d => `${d.value}${d.unit}`);
        
        // Add legend
        this.addLegend(colorScale);
    }
    
    addLegend(colorScale) {
        const legend = this.svg.selectAll('.legend')
            .data(colorScale.domain())
            .enter()
            .append('g')
            .attr('class', 'legend')
            .attr('transform', (d, i) => `translate(${this.width + 10}, ${i * 20})`);
        
        legend.append('rect')
            .attr('width', 15)
            .attr('height', 15)
            .attr('fill', colorScale);
        
        legend.append('text')
            .attr('x', 20)
            .attr('y', 12)
            .style('font-size', '12px')
            .text(d => d.charAt(0).toUpperCase() + d.slice(1).replace('_', ' '));
    }
}

class AlertPerformanceChart {
    constructor(containerId) {
        this.container = d3.select(containerId);
        this.margin = { top: 20, right: 20, bottom: 30, left: 40 };
        this.width = 500 - this.margin.left - this.margin.right;
        this.height = 250 - this.margin.top - this.margin.bottom;
        
        this.svg = null;
        this.data = [];
        
        this.init();
    }
    
    init() {
        this.svg = this.container
            .append('svg')
            .attr('width', this.width + this.margin.left + this.margin.right)
            .attr('height', this.height + this.margin.top + this.margin.bottom)
            .append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);
    }
    
    updateData(alerts) {
        // Process alert performance data
        const performance = this.calculatePerformance(alerts);
        this.data = [
            { metric: 'Sent', value: performance.sent, color: '#2ecc71' },
            { metric: 'Failed', value: performance.failed, color: '#e74c3c' },
            { metric: 'Pending', value: performance.pending, color: '#f39c12' }
        ];
        
        this.render();
    }
    
    calculatePerformance(alerts) {
        return {
            sent: alerts.filter(a => a.status === 'sent').length,
            failed: alerts.filter(a => a.status === 'failed').length,
            pending: alerts.filter(a => a.status === 'pending').length
        };
    }
    
    render() {
        // Create donut chart
        const radius = Math.min(this.width, this.height) / 2;
        const innerRadius = radius * 0.5;
        
        const pie = d3.pie()
            .value(d => d.value)
            .sort(null);
        
        const arc = d3.arc()
            .innerRadius(innerRadius)
            .outerRadius(radius);
        
        // Clear previous content
        this.svg.selectAll('*').remove();
        
        // Center the chart
        const g = this.svg.append('g')
            .attr('transform', `translate(${this.width/2},${this.height/2})`);
        
        // Create arcs
        const arcs = g.selectAll('.arc')
            .data(pie(this.data))
            .enter()
            .append('g')
            .attr('class', 'arc');
        
        arcs.append('path')
            .attr('d', arc)
            .attr('fill', d => d.data.color)
            .transition()
            .duration(750)
            .attrTween('d', function(d) {
                const interpolate = d3.interpolate({ startAngle: 0, endAngle: 0 }, d);
                return function(t) {
                    return arc(interpolate(t));
                };
            });
        
        // Add labels
        arcs.append('text')
            .attr('transform', d => `translate(${arc.centroid(d)})`)
            .attr('text-anchor', 'middle')
            .style('font-size', '12px')
            .style('fill', 'white')
            .text(d => d.data.value > 0 ? d.data.value : '');
        
        // Add center text
        g.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', '0.35em')
            .style('font-size', '14px')
            .style('font-weight', 'bold')
            .text('Alert Status');
    }
}

// Export chart classes for global use
window.ThreatTimeline = ThreatTimeline;
window.SeverityChart = SeverityChart;
window.EnvironmentalChart = EnvironmentalChart;
window.AlertPerformanceChart = AlertPerformanceChart;
