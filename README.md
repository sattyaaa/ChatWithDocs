# QADoc — Intelligent Document QA Assistant

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_19_--_Vite-61DAFB?logo=react)](https://react.dev)
[![Groq](https://img.shields.io/badge/LLM-Groq_GPT--OSS--120B-f55036)](https://groq.com)
[![MongoDB](https://img.shields.io/badge/Vector_Store-MongoDB_Atlas-47A248?logo=mongodb)](https://www.mongodb.com/products/platform/atlas-vector-search)
[![Jina AI](https://img.shields.io/badge/Reranker-Jina_AI_v2-000000)](https://jina.ai)

**QADoc** is an enterprise-grade, agentic Document Question-Answering system. It combines a decoupled **FastAPI** backend running a **LangGraph ReAct Agent** with a **React + Vite** single-page application crafted with a light, distraction-free aesthetic inspired by Claude and ChatGPT.

---

## 🏛️ System Architecture

```mermaid
graph TB
    subgraph UI["Frontend (React + Vite - Port 5173)"]
        CHAT["💬 Chat View\n(Markdown, Citations, Input Dock)"]
        DOCS_TAB["📁 Documents Tab\n(Chunk counts & Deletion)"]
        UPLOAD_MODAL["⬆️ Drag & Drop Uploader\n(Rotating Spinner)"]
    end

    subgraph API["FastAPI Backend (Port 8000)"]
        AUTH_RTR["/api/auth\n(User Login & Registration)"]
        CHAT_RTR["/api/chats\n(History & Auto-Title)"]
        DOC_RTR["/api/documents\n(Upload & Vector Indexing)"]
    end

    subgraph Core["Agentic RAG Engine (src/qadoc)"]
        REACT["LangGraph ReAct Agent\n(Groq openai/gpt-oss-120b)"]
        VSEARCH["Stage 1: Vector Search\n(jina-embeddings-v3)"]
        RERANK["Stage 2: Cross-Encoder\n(Jina Reranker v2)"]
    end

    subgraph DB["Storage"]
        ATLAS_VEC[("MongoDB Atlas\nVector Search")]
        ATLAS_DATA[("MongoDB Atlas\nChats, Messages & Users")]
    end

    UI -->|REST API| API
    CHAT_RTR --> REACT
    DOC_RTR -->|Ephemeral Ingestion| VSEARCH
    REACT -->|retrieve_document_context| VSEARCH
    VSEARCH -->|Top Candidates| RERANK
    RERANK -->|Top-N Reranked| REACT
    VSEARCH <--> ATLAS_VEC
    API <--> ATLAS_DATA
```

---

## 🌟 Key Highlights

* **ReAct Agent Reasoning:** Uses Groq Cloud's `openai/gpt-oss-120b` reasoning model to autonomously formulate search queries, incorporate previous conversation context (auto-rephrasing), and synthesize strictly grounded answers.
* **Two-Stage Retrieval:**
  * **Stage 1 (Atlas Vector Search):** Dense vector similarity matching using `jina-embeddings-v3` (1024 dimensions).
  * **Stage 2 (Jina AI Reranker v2):** Cross-encoder scoring (`jina-reranker-v2-base-multilingual`) to eliminate irrelevant chunks and order excerpts by precise semantic relevance.
* **Ephemeral Ingestion:** Files uploaded (`.pdf`, `.docx`, `.txt`, `.md`) are parsed, split, embedded into MongoDB Atlas, and **immediately deleted from disk** to ensure privacy and zero storage bloat.
* **Document Management Tab:** Each chat features a dedicated `Documents (N)` tab showing all ingested files, vector chunk counts, and one-click vector deletion.
* **Interactive Citations:** Assistant answers cite sources with clickable badges showing document name, page, and match score (e.g. `85% match`), opening full excerpt preview modals.
* **Strict Session Isolation:** Retrieval and document listings are strictly scoped per chat session — no document leaking across different chats.

---

## 📁 Repository Structure

```text
QADoc/
├── backend/
│   ├── app/
│   │   ├── main.py              <-- FastAPI application with CORS and lifespan
│   │   ├── schemas.py           <-- Pydantic request/response models
│   │   └── routers/
│   │       ├── auth.py          <-- /api/auth (Login, Register)
│   │       ├── chats.py         <-- /api/chats (Conversations, QA, Auto-title)
│   │       └── documents.py     <-- /api/documents (Upload, List, Delete)
│   ├── src/qadoc/
│   │   ├── config.py            <-- Central Pydantic settings
│   │   ├── database/            <-- MongoDB connection & session persistence
│   │   └── rag/                 <-- ReAct agent, tools, prompts, & two-stage retrieval
│   ├── pyproject.toml           <-- Backend dependencies
│   ├── uv.lock
│   └── README.md                <-- Backend documentation
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx              <-- Main React application & tab state
│   │   ├── index.css            <-- Claude / ChatGPT light theme styling & animations
│   │   ├── api/client.js        <-- Fetch API client
│   │   └── components/
│   │       ├── Sidebar.jsx      <-- QADoc branding, chat list, & user badge
│   │       ├── ChatDocumentsTab.jsx <-- Ingested files view & deletion
│   │       ├── Citations.jsx    <-- Interactive citation pills & modal
│   │       ├── FileUploadModal.jsx <-- Ingestion modal with rotating spinner
│   │       └── AuthScreen.jsx   <-- User login / registration view
│   ├── vite.config.js           <-- Vite dev server with proxy to :8000
│   ├── package.json
│   └── README.md                <-- Frontend documentation
│
└── README.md                    <-- Project overview
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.11+** with [`uv`](https://docs.astral.sh/uv/) installed.
- **Node.js 18+** with `npm`.
- A **MongoDB Atlas** cluster with an Atlas Vector Search index named `doc_index`.
- API keys for **Groq Cloud** and **Jina AI**.

---

### 2. Configure Backend Environment
Create `backend/.env`:
```env
MONGODB_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=docqa_chat
MONGODB_VECTOR_INDEX=doc_index

GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b

JINA_API_KEY=jina_...
```

---

### 3. Start the Backend Server
```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```
*API docs:* `http://localhost:8000/docs`

---

### 4. Start the Frontend
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
*Web application:* `http://localhost:5173`

---

## 📄 License
This project is licensed under the MIT License.
