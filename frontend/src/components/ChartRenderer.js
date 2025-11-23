import React, { useMemo, memo } from 'react';
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

const ChartRenderer = memo(({ chartConfig }) => {
    const type = chartConfig?.type || 'bar';
    const title = chartConfig?.title || 'Chart';
    const data = chartConfig?.data || [];
    const x_label = chartConfig?.x_label;
    const y_label = chartConfig?.y_label;
    const dataset_label = chartConfig?.dataset_label;

    const labels = data.map(item => item.label);

    const chartData = useMemo(() => ({
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
                fill: type === 'line',
                tension: 0.35,
                segment: type === 'line' ? {
                    borderDash: ctx => {
                        const idx = ctx.p1DataIndex;
                        return data[idx]?.isForecast ? [5, 5] : [];
                    }
                } : undefined,
            },
        ],
    }), [data, labels, dataset_label, type]);

    const options = useMemo(() => ({
        responsive: true,
        maintainAspectRatio: true,
        animation: false,
        plugins: {
            legend: {
                position: 'top',
                display: type !== 'pie',
            },
            title: {
                display: true,
                text: title,
                font: { size: 16, weight: 'bold' },
            },
            tooltip: {
                intersect: false,
                callbacks: {
                    label: function (context) {
                        const item = data[context.dataIndex];
                        return item.tooltip || `${context.dataset.label}: ${context.parsed.y ?? context.parsed}`;
                    },
                },
            },
        },
        scales: type !== 'pie' ? {
            x: {
                title: { display: true, text: x_label || 'X Axis' },
                ticks: {
                    autoSkip: true,
                    maxRotation: 0,
                    callback: (val, idx) => {
                        const lbl = labels[idx];
                        return lbl.length > 12 ? lbl.slice(0, 9) + '…' : lbl;
                    }
                }
            },
            y: {
                title: { display: true, text: y_label || 'Y Axis' },
                beginAtZero: true,
            },
        } : undefined,
    }), [type, title, x_label, y_label, data, labels]);

    if (!chartConfig || data.length === 0) return null;

    return (
        <div style={{
            height: '400px',
            width: '100%',
            maxWidth: '100%',
            overflowX: 'auto',
            paddingBottom: '4px'
        }}>
            {type === 'bar' && <Bar data={chartData} options={options} />}
            {type === 'line' && <Line data={chartData} options={options} />}
            {type === 'pie' && <Pie data={chartData} options={options} />}
        </div>
    );
});

export default ChartRenderer;
