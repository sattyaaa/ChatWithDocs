# Document QA Assistant (RAG Pipeline)

A Streamlit web application to chat with your documents (PDF, Word, Text, Markdown) using a RAG pipeline powered by Weaviate and Groq.

---

## System Architecture

```mermaid
graph TD
    User([User]) <-->|Interacts| UI[Streamlit Frontend - app.py]
    UI <-->|Manage Chats & History| SQLite[(SQLite Database - chat.db)]
    
    subgraph Ingestion Pipeline
        UI -->|Upload Files| Save[Save to data/uploads/]
        Save -->|Load Document| Load[Document Loaders - PDF/Word/TXT/MD]
        Load -->|Split Text| Split[Recursive Text Splitter]
        Split -->|Compute Embeddings| HF[HuggingFace Embeddings - Local]
        HF -->|Store Chunks & Meta| Weaviate[(Weaviate Cloud Database)]
    end

    subgraph RAG Retrieval & Generation
        UI -->|Query RAG| Retrieve[Retrieve Relevant Chunks]
        Weaviate -->|Vector Matches| Retrieve
        Retrieve -->|Assemble Context| Prompt[System Prompt Construction]
        Prompt -->|Invoke Generation| Groq[Groq API - Llama 3.3 70B]
        Groq -->|Response & Sources| UI
    end
```

---

## Technology Stack & Models

### Technology Stack
- **Frontend / UI**: Streamlit
- **Orchestration**: LangChain
- **Vector Database**: Weaviate Cloud
- **Relational Database**: SQLite
- **File Processing**: pypdf, python-docx

### Models
- **Embedding Model**: BAAI/bge-base-en-v1.5
- **Large Language Model (LLM)**: llama-3.3-70b-versatile
---

## Supported File Formats
- PDF (.pdf)
- Microsoft Word (.docx)
- Plain Text (.txt)
- Markdown (.md)

---

## Quick Start

### 1. Installation
```bash
# Clone the repository
git clone <repository-url>
cd QADoc

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here
WEAVIATE_URL=your_weaviate_cluster_url_here
WEAVIATE_API_KEY=your_weaviate_api_key_here
```

### 3. Run the App
```bash
streamlit run app.py
```
Visit `http://localhost:8501` to start.
