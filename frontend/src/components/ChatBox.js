import React, { useState, useEffect, useRef } from 'react';
import { getWebSocketUrl } from '../api';

const ChatBox = () => {
    const [messages, setMessages] = useState([
        { sender: 'bot', text: 'Hello! I am Hermes. Ask me about shipments, delays, or predictions.' }
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
            setMessages((prev) => [...prev, { sender: 'bot', text: message }]);
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

        setMessages((prev) => [...prev, { sender: 'user', text: input }]);
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(input);
        } else {
            setMessages((prev) => [...prev, { sender: 'bot', text: 'Error: Connection lost.' }]);
        }
        setInput('');
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    };

    return (
        <div className="chat-container">
            <div className="messages">
                {messages.map((msg, index) => (
                    <div key={index} className={`message ${msg.sender}`}>
                        <div className="message-content">{msg.text}</div>
                    </div>
                ))}
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
