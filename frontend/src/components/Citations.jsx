import React, { useState } from 'react';
import { FileText, X } from 'lucide-react';

export default function Citations({ sources }) {
  const [selectedDoc, setSelectedDoc] = useState(null);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="citations-wrapper">
      <div className="citations-header">
        <FileText size={13} />
        <span>Referenced Sources ({sources.length})</span>
      </div>

      <div className="citations-badges-grid">
        {sources.map((src, idx) => {
          const scorePercent = src.relevance_score
            ? `${(src.relevance_score * 100).toFixed(0)}% match`
            : null;

          return (
            <button
              key={idx}
              className="citation-pill"
              onClick={() => setSelectedDoc(src)}
              title="Click to view extracted excerpt"
            >
              <FileText size={12} className="text-muted" />
              <span>{src.filename}</span>
              {src.page && <span className="citation-score-tag">p. {src.page}</span>}
              {scorePercent && <span className="citation-score-tag">{scorePercent}</span>}
            </button>
          );
        })}
      </div>

      {/* Modal Drawer to preview the exact text excerpt */}
      {selectedDoc && (
        <div className="modal-overlay" onClick={() => setSelectedDoc(null)}>
          <div className="excerpt-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header" style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-light)' }}>
              <div>
                <div className="modal-title">{selectedDoc.filename}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  {selectedDoc.page ? `Page ${selectedDoc.page}` : 'No page number'}
                  {selectedDoc.relevance_score
                    ? ` • Relevance Score: ${selectedDoc.relevance_score.toFixed(4)}`
                    : ''}
                </div>
              </div>
              <button className="modal-close-btn" onClick={() => setSelectedDoc(null)}>
                <X size={18} />
              </button>
            </div>
            <div className="excerpt-body">
              {selectedDoc.content || 'No text snippet available.'}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
