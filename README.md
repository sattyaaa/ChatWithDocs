# Document QA Assistant (RAG Pipeline)

A Streamlit web application to chat with your documents (PDF, Word, Text, Markdown) using an agentic RAG pipeline powered by Weaviate, MongoDB, and Groq.

---

## System Architecture

Two distinct pipelines operate in this system — one for **indexing documents** and one for **answering queries**. Both converge on the Vector Store.

```mermaid
graph LR
    %% ══════════════════════════════════════════
    %%  FRONTEND
    %% ══════════════════════════════════════════
    FE["Frontend\nStreamlit"]

    %% ══════════════════════════════════════════
    %%  INDEXING PATH
    %% ══════════════════════════════════════════
    subgraph IDX["Indexing Pipeline"]
        direction TB
        A1(["Raw Document"])
        A2["Parse & Chunk"]
        A3["Embed\nbge-base-en-v1.5"]
        A1 --> A2 --> A3
    end

    %% ══════════════════════════════════════════
    %%  QUERY PATH
    %% ══════════════════════════════════════════
    subgraph QRY["Query Pipeline"]
        direction TB
        B1(["User Query"])
        B2["1. History\nLoad context"]
        B3["2. Rephrase\nStandalone query"]
        B4["3. Retrieve\nTop-k similarity search"]
        B5["4. Generate\nGround answer in context"]
        B6(["Answer + Sources"])
        B1 --> B2 --> B3 --> B4 --> B5 --> B6
    end

    %% ══════════════════════════════════════════
    %%  SHARED SERVICES
    %% ══════════════════════════════════════════
    VS[("Vector Store\nWeaviate Cloud")]
    MEM[("Memory Store\nMongoDB Atlas")]
    LLM["LLM\nGroq Cloud"]

    %% ── frontend edges ──
    FE -- "upload document" --> A1
    FE -- "submit query" --> B1
    B6 -- "render response" --> FE
    FE <-. "auth / sessions" .-> MEM

    %% ── cross-pipeline edges ──
    A3 -. stores .-> VS
    B4 <-. retrieves .-> VS
    B2 <-. reads / writes .-> MEM
    B3 <-. rephrase call .-> LLM
    B5 <-. completion call .-> LLM

    %% ══════════════════════════════════════════
    %%  STYLES
    %% ══════════════════════════════════════════
    classDef pipeline  fill:#0f172a,stroke:#475569,color:#e2e8f0
    classDef step      fill:#1e293b,stroke:#6366f1,color:#c7d2fe
    classDef terminal  fill:#1e293b,stroke:#818cf8,color:#e0e7ff,rx:20
    classDef store     fill:#1e293b,stroke:#10b981,color:#6ee7b7
    classDef inference fill:#1e293b,stroke:#f59e0b,color:#fde68a
    classDef frontend  fill:#1e293b,stroke:#38bdf8,color:#bae6fd

    class IDX,QRY pipeline
    class A2,A3,B2,B3,B4,B5 step
    class A1,B1,B6 terminal
    class VS,MEM store
    class LLM inference
    class FE frontend
```

---

## Technology Stack & Models

### Technology Stack
- **Frontend / UI**: Streamlit (modular layout in `ui/`)
- **Orchestration**: LangGraph (compiled state machine workflow)
- **Vector Database**: Weaviate Cloud (with native Multi-Tenancy per user)
- **NoSQL Database**: MongoDB Atlas (persisting chat sessions, history, and users)
- **Caching Layer**: Redis (for caching chat session messages)
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
