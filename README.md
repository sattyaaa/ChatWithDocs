# Document QA Assistant (RAG Pipeline)

A Streamlit web application to chat with your documents (PDF, Word, Text, Markdown) using an agentic RAG pipeline powered by Weaviate, MongoDB, and Groq.

---

## System Architecture

```mermaid
graph TD
    User([👤 User]) <--> UI[Streamlit Frontend]

    UI -->|Upload documents| Ingestion[rag/ingestion.py\nChunk · Embed · Index]
    Ingestion -->|Vectors per-user tenant| VDB[(Weaviate Cloud)]

    UI <-->|Auth & chat sessions| MongoDB[(MongoDB Atlas)]

    UI -->|Ask a question| N1

    subgraph LangGraph["🔁 LangGraph RAG Workflow — rag/graph.py"]
        direction TB
        N1["① load_history\nLoad recent chat turns\nfrom MongoDB"]
        N2["② rephrase_query\nCondense follow-up question\nGroq · llama-3.1-8b-instant"]
        N3["③ retrieve_documents\nVector search by rephrased query\nWeaviate · user tenant"]
        N4["④ generate_answer\nSynthesize answer from context\nGroq · llama-3.3-70b-versatile"]

        N1 --> N2 --> N3 --> N4
    end

    N1 <-->|Recent messages| MongoDB
    N3 <-->|Top-k chunks| VDB
    N4 -->|Answer + source chunks| UI
```

---

## Technology Stack & Models

### Technology Stack
- **Frontend / UI**: Streamlit (modular layout in `ui/`)
- **Orchestration**: LangGraph (compiled state machine workflow)
- **Vector Database**: Weaviate Cloud (with native Multi-Tenancy per user)
- **NoSQL Database**: MongoDB Atlas (persisting chat sessions, history, and users)
- **File Processing**: pypdf, python-docx

### Models
- **Embedding Model**: BAAI/bge-base-en-v1.5
- **Query Rephraser LLM**: `llama-3.1-8b-instant` (via Groq, low-latency)
- **QA Generator LLM**: `llama-3.3-70b-versatile` (via Groq)

---

## Supported File Formats
- PDF (.pdf)
- Microsoft Word (.docx)
- Plain Text (.txt)
- Markdown (.md)

---

## Database Schema

### MongoDB (NoSQL Document Database)
Stored in a remote MongoDB Atlas cluster (`docqa_chat` database) with three collections:
- **users**:
  - `_id` (ObjectId, Primary Key): Unique identifier.
  - `username` (String): Case-insensitive lowercase login username.
  - `password_hash` (String): Hashed password using PBKDF2 HMAC SHA-256 (100k iterations).
  - `created_at` (Date): Creation timestamp.
- **chats**:
  - `_id` / `chat_id` (String, Primary Key): Unique identifier (UUID) for the chat session.
  - `user_id` (String): Owner user's ID string.
  - `title` (String): Title of the chat session.
  - `created_at` (Date): Creation timestamp.
  - `updated_at` (Date): Last updated timestamp.
- **messages**:
  - `_id` (ObjectId, Primary Key): Unique identifier for the message.
  - `chat_id` (String): ID of the parent chat session.
  - `role` (String): Sender role (`user` or `assistant`).
  - `content` (String): The message content.
  - `sources` (Array, Optional): List of source dictionaries `[{"filename": "doc.pdf", "page": 1, "content": "chunk text"}]` for assistant responses.
  - `created_at` (Date): Timestamp when the message was saved.

### Weaviate (Vector Database)
A collection named `Documents` stores the ingested document chunks:
- **Multi-Tenancy**: Native Weaviate partitioning enabled (`use_multi_tenancy=True`). Shard routing uses the logged-in user's MongoDB `user_id` string as the `tenant` key.
- **Properties**:
  - `text` (TEXT): Raw text content of the chunk.
  - `chat_id` (TEXT): ID of the chat session.
  - `document_id` (TEXT): Unique identifier of the source file.
  - `filename` (TEXT): Name of the source file.
  - `page` (INT): Page number of the chunk (0-indexed, applicable for PDFs).
  - `chunk_id` (TEXT): Segment sequence identifier.
  - `source` (TEXT): Source reference path.

---

## Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/sattyaaa/ChatWithDocs.git
cd ChatWithDocs

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here
WEAVIATE_URL=your_weaviate_cluster_url_here
WEAVIATE_API_KEY=your_weaviate_api_key_here
MONGODB_URI=your_mongodb_connection_string_here
```

### 3. Run the App
```bash
streamlit run app.py
```
Visit `http://localhost:8501` to start.
