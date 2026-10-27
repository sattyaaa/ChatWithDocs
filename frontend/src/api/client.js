/**
 * API client for QADoc FastAPI backend.
 * Uses standard fetch with JSON handling.
 */

const BASE_URL = '/api';

export async function loginUser(username, password) {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Login failed');
  }
  return res.json();
}

export async function registerUser(username, password) {
  const res = await fetch(`${BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Registration failed');
  }
  return res.json();
}

export async function fetchChats(userId) {
  const res = await fetch(`${BASE_URL}/chats?user_id=${encodeURIComponent(userId)}`);
  if (!res.ok) {
    throw new Error('Failed to load chat history');
  }
  return res.json();
}

export async function createChat(userId, title = 'New Chat') {
  const res = await fetch(`${BASE_URL}/chats?user_id=${encodeURIComponent(userId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) {
    throw new Error('Failed to create new chat');
  }
  return res.json();
}

export async function deleteChat(chatId, userId) {
  const res = await fetch(`${BASE_URL}/chats/${chatId}?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new Error('Failed to delete chat');
  }
  return res.json();
}

export async function fetchMessages(chatId) {
  const res = await fetch(`${BASE_URL}/chats/${chatId}/messages`);
  if (!res.ok) {
    throw new Error('Failed to load messages');
  }
  return res.json();
}

export async function askQuestion(chatId, userId, query) {
  const res = await fetch(`${BASE_URL}/chats/${chatId}/ask?user_id=${encodeURIComponent(userId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to generate answer');
  }
  return res.json();
}

export async function uploadDocuments(chatId, userId, files) {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }

  const res = await fetch(`${BASE_URL}/documents/upload/${chatId}?user_id=${encodeURIComponent(userId)}`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Upload failed');
  }
  return res.json();
}
