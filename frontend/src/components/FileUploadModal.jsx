import React, { useState, useRef } from 'react';
import { Upload, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { uploadDocuments } from '../api/client';

export default function FileUploadModal({ chatId, userId, isOpen, onClose, onUploadSuccess }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleFileChange = (e) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files));
      setErrorMessage(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      setSelectedFiles(Array.from(e.dataTransfer.files));
      setErrorMessage(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFiles.length) return;
    setIsUploading(true);
    setErrorMessage(null);
    setStatusMessage('Uploading and vector indexing documents via Jina AI...');

    try {
      const results = await uploadDocuments(chatId, userId, selectedFiles);
      const totalChunks = results.reduce((acc, r) => acc + (r.chunks_ingested || 0), 0);

      setStatusMessage(`Ingested ${results.length} file(s) into ${totalChunks} searchable chunks.`);
      setSelectedFiles([]);
      setTimeout(() => {
        setIsUploading(false);
        setStatusMessage(null);
        if (onUploadSuccess) onUploadSuccess();
        onClose();
      }, 1500);
    } catch (err) {
      setIsUploading(false);
      setErrorMessage(err.message || 'Upload failed');
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Upload Documents</h3>
          <button className="modal-close-btn" onClick={onClose} disabled={isUploading}>
            <X size={18} />
          </button>
        </div>

        <div
          className="dropzone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload size={32} className="dropzone-icon" />
          <div className="dropzone-text">Click or drag files here to upload</div>
          <div className="dropzone-subtext">Supported formats: PDF, DOCX, TXT, Markdown</div>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            multiple
            accept=".pdf,.docx,.txt,.md"
            style={{ display: 'none' }}
          />
        </div>

        {selectedFiles.length > 0 && (
          <div style={{ marginTop: '14px', fontSize: '13px' }}>
            <div style={{ fontWeight: 600, marginBottom: '6px' }}>Selected files ({selectedFiles.length}):</div>
            <ul style={{ paddingLeft: '18px', color: 'var(--text-secondary)' }}>
              {selectedFiles.map((f, i) => (
                <li key={i}>{f.name} ({(f.size / 1024).toFixed(0)} KB)</li>
              ))}
            </ul>
          </div>
        )}

        {statusMessage && (
          <div style={{ marginTop: '14px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#16a34a' }}>
            {isUploading ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
            <span>{statusMessage}</span>
          </div>
        )}

        {errorMessage && (
          <div style={{ marginTop: '14px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#dc2626' }}>
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
          <button
            onClick={onClose}
            className="action-icon-btn"
            disabled={isUploading}
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            className="auth-btn-primary"
            style={{ width: 'auto', padding: '8px 18px', marginTop: 0, display: 'flex', alignItems: 'center', gap: '8px' }}
            disabled={isUploading || selectedFiles.length === 0}
          >
            {isUploading && <Loader2 size={15} className="animate-spin" />}
            <span>{isUploading ? 'Indexing Chunks...' : 'Process & Ingest'}</span>
          </button>

        </div>
      </div>
    </div>
  );
}
