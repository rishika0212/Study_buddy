const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export const chatApi = {
  async sendMessage(userId: string, message: string) {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_id: userId, message }),
    });
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  async getProfile(userId: string) {
    const response = await fetch(`${API_BASE_URL}/user/${userId}/profile`);
    if (!response.ok) {
      throw new Error('Failed to fetch profile');
    }
    return response.json();
  },

  async getTopics(userId: string) {
    const response = await fetch(`${API_BASE_URL}/user/${userId}/topics`);
    if (!response.ok) {
      throw new Error('Failed to fetch topics');
    }
    return response.json();
  },

  async getHistory(userId: string) {
    const response = await fetch(`${API_BASE_URL}/user/${userId}/history`);
    if (!response.ok) {
      throw new Error('Failed to fetch history');
    }
    return response.json();
  },

  async resetMemory(userId: string) {
    const response = await fetch(`${API_BASE_URL}/user/${userId}/reset`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to reset memory');
    }
    return response.json();
  },

  async clearHistory(userId: string) {
    const response = await fetch(`${API_BASE_URL}/user/${userId}/clear-history`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to clear history');
    }
    return response.json();
  },

  async generateMCQ(userId: string, topic: string) {
    const response = await fetch(`${API_BASE_URL}/assessment/mcq/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, topic }),
    });
    if (!response.ok) throw new Error('Failed to generate MCQ');
    return response.json();
  },

  async submitMCQ(userId: string, topic: string, answer: string) {
    const response = await fetch(`${API_BASE_URL}/assessment/mcq/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, topic, user_answer: answer }),
    });
    if (!response.ok) throw new Error('Failed to submit MCQ');
    return response.json();
  },

  async generateQnA(userId: string, topic: string, length: string = "medium") {
    const response = await fetch(`${API_BASE_URL}/assessment/qna/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, topic, length }),
    });
    if (!response.ok) throw new Error('Failed to generate Q&A');
    return response.json();
  },

  async submitQnA(userId: string, topic: string, answer: string) {
    const response = await fetch(`${API_BASE_URL}/assessment/qna/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, topic, user_answer: answer }),
    });
    if (!response.ok) throw new Error('Failed to submit Q&A');
    return response.json();
  },

  async getAreas(userId: string) {
    const response = await fetch(`${API_BASE_URL}/areas/get`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    if (!response.ok) throw new Error('Failed to get learning areas');
    return response.json();
  },
};
