import { useState, useCallback, useEffect } from 'react';
import { chatApi } from '../services/api';
import type { Message } from '../components/MessageBubble';

export const useChat = (userId: string) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch messages on load - topic-centric model, no sessions
  useEffect(() => {
    const fetchHistory = async () => {
      setIsLoading(true);
      try {
        const history = await chatApi.getHistory(userId);
        const formattedHistory = history.map((msg: any, index: number) => ({
          id: `hist_${index}`,
          text: msg.text,
          sender: msg.sender,
          timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date()
        }));
        setMessages(formattedHistory);
      } catch (err) {
        console.error("Failed to fetch history", err);
        setMessages([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchHistory();
  }, [userId]);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const data = await chatApi.sendMessage(userId, text);
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: data.response,
        sender: 'ai',
        timestamp: new Date(),
        metadata: data.metadata
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  // Clear messages locally and on the backend (for "New Session")
  const clearMessages = useCallback(async () => {
    try {
      await chatApi.clearHistory(userId);
      setMessages([]);
    } catch (err) {
      console.error("Failed to clear history", err);
      // Still clear locally even if backend fails
      setMessages([]);
    }
  }, [userId]);

  return { messages, isLoading, error, sendMessage, clearMessages };
};
