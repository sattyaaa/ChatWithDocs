import React, { useState, useEffect } from 'react';
import {
  FileText,
  Trash2,
  Upload,
  Loader2,
  AlertCircle,
  CheckCircle,
  FileBox,
  Layers,
} from 'lucide-react';
import { fetchChatDocuments, deleteDocument } from '../api/client';

export default function ChatDocumentsTab({
  chatId,
  userId,
  onUploadClick,
  onDocumentChange,
}) {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [deletingFilename, setDeletingFilename] = useState(null);
  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    if (chatId && userId) {
      loadDocuments();
    }
  }, [chatId, userId]);

  const loadDocuments = async () => {
    setIsLoading(true);
    setFeedback(null);
    try {
      const docs = await fetchChatDocuments(chatId, userId);
      setDocuments(docs);
      if (onDocumentChange) onDocumentChange(docs.length);
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Failed to load documents' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (filename) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"? All indexed vector embeddings will be removed.`)) {
      return;
    }

    setDeletingFilename(filename);
    try {
      const res = await deleteDocument(chatId, filename, userId);
      setFeedback({
        type: 'success',
        message: `Deleted "${filename}" (${res.deleted_chunks} chunks removed).`,
      });
      // Refresh document list
      const updated = documents.filter((d) => d.filename !== filename);
      setDocuments(updated);
      if (onDocumentChange) onDocumentChange(updated.length);
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Deletion failed' });
    } finally {
      setDeletingFilename(null);
    }
  };

  return (
    <div className="documents-tab-container">
      {/* Tab Header */}
      <div className="documents-tab-header">
        <div>
          <h2 className="documents-tab-title">Ingested Documents</h2>
          <p className="documents-tab-subtitle">
            Files indexed in MongoDB Atlas vector store for this chat session.
          </p>
        </div>

        <button className="action-icon-btn primary-action" onClick={onUploadClick}>
          <Upload size={14} />
          <span>Upload Document</span>
        </button>
      </div>

      {/* Feedback Alert */}
      {feedback && (
        <div className={`feedback-banner ${feedback.type}`}>
          {feedback.type === 'success' ? (
            <CheckCircle size={16} />
          ) : (
            <AlertCircle size={16} />
          )}
          <span>{feedback.message}</span>
        </div>
      )}

      {/* Loading State */}
      {isLoading ? (
        <div className="documents-loading">
          <Loader2 size={24} className="animate-spin" />
          <span>Loading ingested documents...</span>
        </div>
      ) : documents.length === 0 ? (
        /* Empty State */
        <div className="documents-empty-state">
          <div className="empty-icon-wrap">
            <FileBox size={36} />
          </div>
          <h3>No documents attached yet</h3>
          <p>
            Upload PDF, Word (DOCX), Text, or Markdown documents to enable AI vector search
            and grounded question answering.
          </p>
          <button className="action-icon-btn primary-action" onClick={onUploadClick}>
            <Upload size={15} />
            <span>Upload First Document</span>
          </button>
        </div>
      ) : (
        /* Documents Grid / List */
        <div className="documents-grid">
          {documents.map((doc) => {
            const isDeleting = deletingFilename === doc.filename;
            return (
              <div key={doc.filename} className="document-card">
                <div className="document-card-main">
                  <div className="document-file-icon">
                    <FileText size={20} />
                  </div>

                  <div className="document-file-info">
                    <div className="document-file-name" title={doc.filename}>
                      {doc.filename}
                    </div>
                    <div className="document-file-meta">
                      <span className="document-chunk-badge">
                        <Layers size={11} />
                        {doc.chunks_count} chunks indexed
                      </span>
                    </div>
                  </div>
                </div>

                <div className="document-card-actions">
                  <button
                    className="document-delete-btn"
                    title={`Delete ${doc.filename}`}
                    disabled={isDeleting}
                    onClick={() => handleDelete(doc.filename)}
                  >
                    {isDeleting ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Trash2 size={16} />
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
