import React, { useEffect, useState } from 'react';
import './App.css';
import ChatBox from './components/ChatBox';
import { fetchData } from './api';

function App() {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetchData().then((data) => setData(data));
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Hermes Logistics Assistant</h1>
      </header>
      <div className="main-content">
        <div className="chat-section">
          <ChatBox />
        </div>
        <div className="data-section">
          <h2>Shipment Data</h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Route</th>
                  <th>Warehouse</th>
                  <th>Date</th>
                  <th>Delay (min)</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    <td>{row.route}</td>
                    <td>{row.warehouse}</td>
                    <td>{new Date(row.date).toLocaleDateString()}</td>
                    <td className={row.delay_minutes > 0 ? 'delayed' : ''}>
                      {row.delay_minutes}
                    </td>
                    <td>{row.delay_reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
