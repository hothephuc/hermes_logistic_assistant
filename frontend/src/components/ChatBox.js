import React, { useState, useEffect, useRef } from 'react';
import { getWebSocketUrl } from '../api';
import ChartRenderer from './ChartRenderer';
import TableRenderer from './TableRenderer';

const ChatBox = () => {
    const [messages, setMessages] = useState([
        {
            sender: 'bot',
            text: 'Hello! I am Hermes. Ask me about shipments, delays, or predictions.',
            type: 'text'
        }
    ]);
    const [input, setInput] = useState('');
    const ws = useRef(null);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        ws.current = new WebSocket(getWebSocketUrl());

        ws.current.onopen = () => {
            console.log('Connected to WebSocket');
        };

        ws.current.onmessage = (event) => {
            const message = event.data;

            // Try to parse JSON response
            try {
                const parsed = JSON.parse(message);
                if (parsed.result) {
                    const { summary, chart, table } = parsed.result;

                    // Add text summary
                    if (summary) {
                        setMessages((prev) => [...prev, {
                            sender: 'bot',
                            text: summary,
                            type: 'text'
                        }]);
                    }

                    // Add chart if present
                    if (chart) {
                        setMessages((prev) => [...prev, {
                            sender: 'bot',
                            chartConfig: chart,
                            type: 'chart'
                        }]);
                    }

                    // Add table if present
                    if (table) {
                        setMessages((prev) => [...prev, {
                            sender: 'bot',
                            tableConfig: table,
                            type: 'table'
                        }]);
                    }
                } else {
                    // Fallback to plain text
                    setMessages((prev) => [...prev, {
                        sender: 'bot',
                        text: message,
                        type: 'text'
                    }]);
                }
            } catch (error) {
                // If not JSON, display as plain text
                setMessages((prev) => [...prev, {
                    sender: 'bot',
                    text: message,
                    type: 'text'
                }]);
            }
        };

        ws.current.onclose = () => {
            console.log('Disconnected from WebSocket');
        };

        return () => {
            if (ws.current) {
                ws.current.close();
            }
        };
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const sendMessage = () => {
        if (!input.trim()) return;

        setMessages((prev) => [...prev, { sender: 'user', text: input, type: 'text' }]);
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(input);
        } else {
            setMessages((prev) => [...prev, {
                sender: 'bot',
                text: 'Error: Connection lost.',
                type: 'text'
            }]);
        }
        setInput('');
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    };

    const renderMessage = (msg, index) => {
        if (msg.type === 'chart') {
            return (
                <div key={index} className="message bot">
                    <div className="message-content">
                        <ChartRenderer chartConfig={msg.chartConfig} />
                    </div>
                </div>
            );
        }

        if (msg.type === 'table') {
            return (
                <div key={index} className="message bot">
                    <div className="message-content">
                        <TableRenderer tableConfig={msg.tableConfig} />
                    </div>
                </div>
            );
        }

        return (
            <div key={index} className={`message ${msg.sender}`}>
                <div className="message-content">{msg.text}</div>
            </div>
        );
    };

    return (
        <div className="chat-container">
            <div className="messages">
                {messages.map(renderMessage)}
                <div ref={messagesEndRef} />
            </div>
            <div className="input-area">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask a question..."
                />
                <button onClick={sendMessage}>Send</button>
            </div>
        </div>
    );
};

export default ChatBox;
