import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  ArrowUp,
  Paperclip,
  Upload,
  BookOpen,
  Sparkles,
  Loader2,
  MessageSquare,
  FileText,
} from 'lucide-react';

import {
  fetchChats,
  createChat,
  deleteChat,
  fetchMessages,
  askQuestion,
  fetchChatDocuments,
} from './api/client';

import Sidebar from './components/Sidebar';
import Citations from './components/Citations';
import FileUploadModal from './components/FileUploadModal';
import AuthScreen from './components/AuthScreen';
import ChatDocumentsTab from './components/ChatDocumentsTab';

export default function App() {
  // 1. Auth State (persisted in localStorage)
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('qadoc_user');
    return saved ? JSON.parse(saved) : null;
  });

  // 2. Chat, Tabs & Message State
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'documents'
  const [docCount, setDocCount] = useState(0);
  const [messages, setMessages] = useState([]);
  const [inputPrompt, setInputPrompt] = useState('');
  const [isLoadingAnswer, setIsLoadingAnswer] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Sync user with localStorage
  const handleAuthSuccess = (userData) => {

    setUser(userData);
    localStorage.setItem('qadoc_user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('qadoc_user');
    setChats([]);
    setActiveChatId(null);
    setMessages([]);
  };

  // Load chats on login
  useEffect(() => {
    if (user?.user_id) {
      loadChats();
    }
  }, [user]);

  const loadChats = async () => {
    try {
      const data = await fetchChats(user.user_id);
      setChats(data);
      if (data.length > 0 && !activeChatId) {
        setActiveChatId(data[0].chat_id);
      }
    } catch (err) {
      console.error('Failed to load chats:', err);
    }
  };

  // Load messages and document count when active chat changes
  useEffect(() => {
    if (activeChatId) {
      loadMessages(activeChatId);
      loadDocCount(activeChatId);
    } else {
      setMessages([]);
      setDocCount(0);
    }
  }, [activeChatId]);

  const loadDocCount = async (chatId) => {
    if (!user?.user_id) return;
    try {
      const docs = await fetchChatDocuments(chatId, user.user_id);
      setDocCount(docs.length);
    } catch (err) {
      console.warn('Failed to fetch doc count:', err);
    }
  };

  const loadMessages = async (chatId) => {
    try {
      const msgs = await fetchMessages(chatId);
      setMessages(msgs);
      scrollToBottom();
    } catch (err) {
      console.error('Failed to load messages:', err);
    }
  };


  const scrollToBottom = () => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  // Start a new chat
  const handleNewChat = async () => {
    if (!user) return;
    try {
      const newChat = await createChat(user.user_id, 'New Chat');
      setChats((prev) => [newChat, ...prev]);
      setActiveChatId(newChat.chat_id);
      setMessages([]);
    } catch (err) {
      alert('Failed to create new chat: ' + err.message);
    }
  };

  // Delete chat
  const handleDeleteChat = async (chatId) => {
    try {
      await deleteChat(chatId, user.user_id);
      setChats((prev) => prev.filter((c) => c.chat_id !== chatId));
      if (activeChatId === chatId) {
        const remaining = chats.filter((c) => c.chat_id !== chatId);
        setActiveChatId(remaining.length > 0 ? remaining[0].chat_id : null);
      }
    } catch (err) {
      alert('Failed to delete chat: ' + err.message);
    }
  };

  // Send message & generate answer (whole answer at once)
  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    const query = inputPrompt.trim();
    if (!query || isLoadingAnswer) return;

    let targetChatId = activeChatId;

    // If no chat is active, automatically start one
    if (!targetChatId) {
      try {
        const newChat = await createChat(user.user_id, query.slice(0, 30));
        setChats((prev) => [newChat, ...prev]);
        setActiveChatId(newChat.chat_id);
        targetChatId = newChat.chat_id;
      } catch (err) {
        alert('Failed to initialize chat: ' + err.message);
        return;
      }
    }

    // 1. Optimistic user message bubble
    const userMsg = { role: 'user', content: query, sources: [] };
    setMessages((prev) => [...prev, userMsg]);
    setInputPrompt('');
    setIsLoadingAnswer(true);
    scrollToBottom();

    // Auto-reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    // 2. Call ReAct Agent QA endpoint
    try {
      const res = await askQuestion(targetChatId, user.user_id, query);
      const assistantMsg = {
        role: 'assistant',
        content: res.answer,
        sources: res.sources || [],
      };
      setMessages((prev) => [...prev, assistantMsg]);
      if (res.chat_title) {
        setChats((prev) =>
          prev.map((c) => (c.chat_id === targetChatId ? { ...c, title: res.chat_title } : c))
        );
      } else {
        loadChats();
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ **Error generating answer:** ${err.message}`,
          sources: [],
        },
      ]);
    } finally {
      setIsLoadingAnswer(false);
      scrollToBottom();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Auto-resize input textarea
  const handleInputResize = (e) => {
    setInputPrompt(e.target.value);
    const target = e.target;
    target.style.height = 'auto';
    target.style.height = `${Math.min(target.scrollHeight, 160)}px`;
  };

  if (!user) {
    return <AuthScreen onAuthSuccess={handleAuthSuccess} />;
  }

  const currentChat = chats.find((c) => c.chat_id === activeChatId);

  return (
    <div className="app-container">
      {/* 1. Collapsible Sidebar */}
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={(id) => setActiveChatId(id)}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        username={user.username}
        onLogout={handleLogout}
      />

      {/* 2. Main Chat Area */}
      <main className="chat-main">
        {/* Top Header Bar */}
        <header className="top-bar">
          <div className="top-bar-left">
            <div className="chat-title-display">
              {currentChat?.title || 'Document QA'}
            </div>

            {/* Navigation Tabs (Chat vs Documents) */}
            <div className="chat-tabs-nav">
              <button
                className={`chat-tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
                onClick={() => setActiveTab('chat')}
              >
                <MessageSquare size={13} />
                <span>Chat</span>
              </button>

              <button
                className={`chat-tab-btn ${activeTab === 'documents' ? 'active' : ''}`}
                onClick={() => setActiveTab('documents')}
              >
                <FileText size={13} />
                <span>Documents</span>
                <span className="tab-count-badge">{docCount}</span>
              </button>
            </div>
          </div>

          <div className="top-bar-actions">
            <span className="model-badge">Groq GPT-OSS-120B • ReAct</span>
            <button
              className="action-icon-btn primary-action"
              onClick={() => {
                if (!activeChatId) {
                  handleNewChat().then(() => setIsUploadModalOpen(true));
                } else {
                  setIsUploadModalOpen(true);
                }
              }}
            >
              <Upload size={14} />
              <span>Upload Document</span>
            </button>
          </div>
        </header>

        {/* Tab Content: Documents View vs Message Stream */}
        {activeTab === 'documents' ? (
          <ChatDocumentsTab
            chatId={activeChatId}
            userId={user?.user_id}
            onUploadClick={() => setIsUploadModalOpen(true)}
            onDocumentChange={(count) => setDocCount(count)}
          />
        ) : (
          <>
            {/* Message Stream */}
            <div className="messages-container">
              <div className="messages-inner">
                {messages.length === 0 ? (
                  <div className="welcome-screen">
                    <div className="welcome-icon">
                      <BookOpen size={28} />
                    </div>
                    <h1 className="welcome-title">What would you like to know?</h1>
                    <p className="welcome-subtitle">
                      Upload documents (**PDF, DOCX, TXT, Markdown**) to search with vector similarity,
                      rerank with Jina AI, and get grounded answers from the ReAct agent.
                    </p>
                    <button
                      className="action-icon-btn primary-action"
                      style={{ padding: '9px 18px', fontSize: '13.5px' }}
                      onClick={() => setIsUploadModalOpen(true)}
                    >
                      <Upload size={15} />
                      <span>Attach Documents to this Chat</span>
                    </button>
                  </div>
                ) : (
                  messages.map((msg, idx) => (
                    <div key={idx} className={`message-row ${msg.role}`}>
                      {msg.role === 'user' ? (
                        <div className="message-bubble-user">{msg.content}</div>
                      ) : (
                        <div className="message-bubble-assistant">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content}
                          </ReactMarkdown>
                          {msg.sources && msg.sources.length > 0 && (
                            <Citations sources={msg.sources} />
                          )}
                        </div>
                      )}
                    </div>
                  ))
                )}

                {/* Loading Indicator */}
                {isLoadingAnswer && (
                  <div className="message-row assistant">
                    <div className="message-bubble-assistant" style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--text-secondary)' }}>
                      <Loader2 size={18} className="animate-spin text-accent" />
                      <span className="animate-pulse" style={{ fontSize: '14px', fontWeight: 500 }}>
                        Searching documents & reasoning with Groq ReAct agent...
                      </span>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* 3. Floating Bottom Input Dock */}
            <div className="input-dock">
              <form className="input-container" onSubmit={handleSendMessage}>
                <button
                  type="button"
                  className="attach-btn"
                  title="Upload documents"
                  onClick={() => setIsUploadModalOpen(true)}
                >
                  <Paperclip size={18} />
                </button>

                <textarea
                  ref={textareaRef}
                  rows={1}
                  className="prompt-textarea"
                  placeholder="Ask anything about your documents..."
                  value={inputPrompt}
                  onChange={handleInputResize}
                  onKeyDown={handleKeyDown}
                  disabled={isLoadingAnswer}
                />

                <button
                  type="submit"
                  className="send-btn"
                  disabled={!inputPrompt.trim() || isLoadingAnswer}
                  title="Send message"
                >
                  {isLoadingAnswer ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <ArrowUp size={16} />
                  )}
                </button>
              </form>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>
                QADoc uses hybrid vector search + cross-encoder reranking. Verify citations for accuracy.
              </div>
            </div>
          </>
        )}
      </main>

      {/* 4. Document Ingestion Modal */}
      <FileUploadModal
        chatId={activeChatId}
        userId={user?.user_id}
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={() => {
          if (activeChatId) {
            loadMessages(activeChatId);
            loadDocCount(activeChatId);
          }
        }}
      />

    </div>
  );
}
