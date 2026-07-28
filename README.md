# Document QA Assistant (RAG Pipeline)

A Streamlit web application to chat with your documents (PDF, Word, Text, Markdown) using an agentic RAG pipeline powered by Weaviate, MongoDB, and Groq.

---

## System Architecture

```mermaid
graph TD
    User([User]) <--> UI_Controller[Streamlit UI Controller: app.py]
    
    subgraph UI Package [ui/]
        UI_Controller -->|Renders| UI_Auth[Authentication: auth.py]
        UI_Controller -->|Renders| UI_Sidebar[Sidebar & History: sidebar.py]
        UI_Controller -->|Renders| UI_Uploader[Document Uploader: uploader.py]
        UI_Controller -->|Renders| UI_Components[Source Badges: components.py]
    end

    UI_Auth -->|Authenticate / Register| Auth[Auth Logic: database/auth.py]
    Auth <--> DB_Users[(MongoDB: users collection)]

    UI_Uploader -->|Process Files| Ingestion[Ingestion: rag/ingestion.py]
    Ingestion -->|Ingest under Tenant user_id| Weaviate[(Weaviate Cloud)]

    UI_Controller -->|Ask Question| Graph[LangGraph Workflow: rag/graph.py]

    subgraph LangGraph State Machine
        Graph -->|Node 1: load_history| Node_History[Load History]
        Node_History <--> DB_Messages[(MongoDB: chats & messages)]
        
        Node_History -->|Node 2: rephrase_query| Node_Rephrase[Rephrase Query]
        Node_Rephrase -->|Condense context| LLM_Rephrase[Groq: Llama 3.1 8B Instant]
        
        Node_Rephrase -->|Node 3: retrieve_documents| Node_Retrieve[Retrieve Documents]
        Node_Retrieve -->|Multi-Tenant Query| Weaviate
        
        Node_Retrieve -->|Node 4: generate_answer| Node_Generate[Generate Answer]
        Node_Generate -->|Context QA| LLM_QA[Groq: Llama 3.3 70B Versatile]
    end

    Node_Generate -->|Response & Sources| UI_Controller
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
