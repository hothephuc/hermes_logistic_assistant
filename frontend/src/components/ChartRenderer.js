import React from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    ArcElement,
    Title,
    Tooltip,
    Legend,
    Filler
} from 'chart.js';
import { Bar, Line, Pie } from 'react-chartjs-2';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    ArcElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

const ChartRenderer = ({ chartConfig }) => {
    if (!chartConfig || !chartConfig.data) {
        return null;
    }

    const { type, title, data, x_label, y_label, dataset_label } = chartConfig;

    // Build chart data structure for Chart.js
    const labels = data.map(item => item.label);

    const chartData = {
        labels,
        datasets: [
            {
                label: dataset_label || 'Dataset',
                data: data.map(item => item.value),
                backgroundColor: type === 'pie'
                    ? [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 206, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)',
                        'rgba(255, 159, 64, 0.8)',
                    ]
                    : data.map(item => item.isForecast
                        ? 'rgba(255, 159, 64, 0.6)'
                        : 'rgba(54, 162, 235, 0.8)'
                    ),
                borderColor: type === 'line'
                    ? data.map(item => item.isForecast
                        ? 'rgba(255, 159, 64, 1)'
                        : 'rgba(54, 162, 235, 1)'
                    )
                    : 'rgba(54, 162, 235, 1)',
                borderWidth: 2,
                borderDash: type === 'line' ? data.map(item => item.isForecast ? [5, 5] : []) : undefined,
                fill: type === 'line',
                tension: 0.4,
            },
        ],
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                display: type !== 'pie',
            },
            title: {
                display: true,
                text: title || 'Chart',
                font: {
                    size: 16,
                    weight: 'bold',
                },
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        const item = data[context.dataIndex];
                        return item.tooltip || `${context.dataset.label}: ${context.parsed.y || context.parsed}`;
                    },
                },
            },
        },
        scales: type !== 'pie' ? {
            x: {
                title: {
                    display: true,
                    text: x_label || 'X Axis',
                },
            },
            y: {
                title: {
                    display: true,
                    text: y_label || 'Y Axis',
                },
                beginAtZero: true,
            },
        } : undefined,
    };

    return (
        <div style={{ height: '400px', marginTop: '20px' }}>
            {type === 'bar' && <Bar data={chartData} options={options} />}
            {type === 'line' && <Line data={chartData} options={options} />}
            {type === 'pie' && <Pie data={chartData} options={options} />}
        </div>
    );
};

export default ChartRenderer;
