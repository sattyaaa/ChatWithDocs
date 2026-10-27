import React from 'react';
import { Plus, MessageSquare, Trash2, LogOut, User, BookOpen } from 'lucide-react';

export default function Sidebar({
  chats,
  activeChatId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  username,
  onLogout,
}) {
  return (
    <aside className="sidebar">
      {/* 1. Application Brand Header */}
      <div className="brand-header">
        <div className="brand-logo-icon">
          <BookOpen size={18} />
        </div>
        <div className="brand-info">
          <span className="brand-title">QADoc</span>
          <span className="brand-tagline">Document Intelligence</span>
        </div>
      </div>

      <div className="sidebar-header">
        <button className="new-chat-btn" onClick={onNewChat}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <MessageSquare size={16} />
            <span>New Chat</span>
          </span>
          <Plus size={16} />
        </button>
      </div>


      <div className="chats-list">
        <div className="chats-section-title">Your Conversations</div>
        {chats.length === 0 ? (
          <div style={{ padding: '16px 8px', fontSize: '13px', color: 'var(--text-muted)' }}>
            No chats yet. Start a new one!
          </div>
        ) : (
          chats.map((chat) => {
            const isActive = chat.chat_id === activeChatId;
            return (
              <div
                key={chat.chat_id}
                className={`chat-item ${isActive ? 'active' : ''}`}
                onClick={() => onSelectChat(chat.chat_id)}
              >
                <span className="chat-item-title">{chat.title || 'New Chat'}</span>
                <button
                  className="chat-delete-btn"
                  title="Delete chat"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm('Delete this chat and its documents?')) {
                      onDeleteChat(chat.chat_id);
                    }
                  }}
                >
                  <Trash2 size={13} />
                </button>
              </div>
            );
          })
        )}
      </div>

      <div className="sidebar-footer">
        <div className="user-badge">
          <div className="avatar-circle">
            {username ? username.charAt(0).toUpperCase() : <User size={14} />}
          </div>
          <span style={{ fontWeight: 500, maxWidth: '130px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {username || 'User'}
          </span>
        </div>
        <button className="logout-btn" onClick={onLogout} title="Log out">
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
}
