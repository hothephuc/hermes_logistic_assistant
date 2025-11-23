import React from 'react';

const TableRenderer = ({ tableConfig }) => {
    if (!tableConfig || !tableConfig.columns) {
        return null;
    }

    const { columns, rows, forecast } = tableConfig;

    return (
        <div style={{ marginTop: '20px', overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                <thead>
                    <tr style={{ backgroundColor: '#f0f0f0' }}>
                        {columns.map((col, idx) => (
                            <th key={idx} style={{
                                border: '1px solid #ddd',
                                padding: '12px',
                                textAlign: 'left',
                                fontWeight: 'bold'
                            }}>
                                {col.label}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {rows && rows.map((row, rowIdx) => (
                        <tr key={rowIdx} style={{
                            backgroundColor: rowIdx % 2 === 0 ? '#fff' : '#f9f9f9'
                        }}>
                            {columns.map((col, colIdx) => (
                                <td key={colIdx} style={{
                                    border: '1px solid #ddd',
                                    padding: '10px'
                                }}>
                                    {row[col.key] !== undefined && row[col.key] !== null
                                        ? String(row[col.key])
                                        : '-'}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>

            {forecast && forecast.length > 0 && (
                <div style={{ marginTop: '20px' }}>
                    <h4>Forecast (Next Week)</h4>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                        <thead>
                            <tr style={{ backgroundColor: '#fff3cd' }}>
                                <th style={{
                                    border: '1px solid #ddd',
                                    padding: '12px',
                                    textAlign: 'left',
                                    fontWeight: 'bold'
                                }}>
                                    Date
                                </th>
                                <th style={{
                                    border: '1px solid #ddd',
                                    padding: '12px',
                                    textAlign: 'left',
                                    fontWeight: 'bold'
                                }}>
                                    Predicted Avg Delay (min)
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {forecast.map((item, idx) => (
                                <tr key={idx} style={{
                                    backgroundColor: idx % 2 === 0 ? '#fffaeb' : '#fff3cd'
                                }}>
                                    <td style={{ border: '1px solid #ddd', padding: '10px' }}>
                                        {String(item.date)}
                                    </td>
                                    <td style={{ border: '1px solid #ddd', padding: '10px' }}>
                                        {item.predicted_avg_delay.toFixed(2)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default TableRenderer;
