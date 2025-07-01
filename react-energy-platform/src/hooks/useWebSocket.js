import { useState, useEffect, useRef } from 'react';

const useWebSocket = (url) => {
  const [socket, setSocket] = useState(null);
  const [lastMessage, setLastMessage] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const messageQueue = useRef([]);

  useEffect(() => {
    if (!url) return;

    const ws = new WebSocket(url);
    setSocket(ws);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      // Send any queued messages
      messageQueue.current.forEach(msg => ws.send(JSON.stringify(msg)));
      messageQueue.current = [];
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        setLastMessage(message);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
        setLastMessage(event.data); // Store as raw data if not JSON
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      setSocket(null);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, [url]);

  const sendMessage = (message) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message));
    } else {
      // Queue message if socket is not ready
      messageQueue.current.push(message);
      console.log('WebSocket not ready, message queued.');
    }
  };

  return { lastMessage, sendMessage, isConnected, readyState: socket?.readyState };
};

export default useWebSocket;
