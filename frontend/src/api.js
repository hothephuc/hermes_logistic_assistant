const API_BASE_URL = "http://localhost:8000/api";
const WS_BASE_URL = "ws://localhost:8000/api/ws";

export const fetchData = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/data`);
        if (!response.ok) {
            throw new Error("Network response was not ok");
        }
        return await response.json();
    } catch (error) {
        console.error("Error fetching data:", error);
        return [];
    }
};

export const getWebSocketUrl = () => {
    return `${WS_BASE_URL}/chat`;
};
