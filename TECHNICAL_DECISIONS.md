# Technical Decisions and Reasoning Log

This document records the architectural choices of **QADoc** and directly addresses the seven reasoning challenges in **Problem Statement 1**.

---

## Part 1: Three Core Architectural Decisions

### 1. Two-Stage Retrieval vs. Naive Vector Search
- **Context:** Standard single-stage RAG retrieves top-k chunks by bi-encoder cosine distance and sends all of them to the LLM.
- **Decision:** Use MongoDB Atlas Vector Search (`fetch_k=15`) for broad candidate recall, followed by Jina AI Reranker v2 cross-encoder attention to pick the top 3-5 passages.
- **Justification:** Bi-encoders compress text into single vectors, losing fine token interactions. Cross-encoders calculate true all-to-all attention between query and passage tokens. Reranking 15 pre-filtered chunks takes under 250ms and eliminates irrelevant passages before the prompt is assembled.

### 2. LangGraph ReAct Agent vs. Static Linear Chains
- **Context:** Real user queries are often informal or ambiguous, failing exact-keyword lookups.
- **Decision:** Implement an autonomous ReAct loop powered by `openai/gpt-oss-120b` on Groq, equipped with `retrieve_document_context`.
- **Justification:** The agent enriches queries with domain synonyms before retrieval (e.g., rewriting *"What dataset was used?"* to *"parallel corpus sentence pairs Spanish English training data"*), handles follow-ups, and bypasses retrieval on casual greetings (*"hello"*) for sub-400ms responses.

### 3. Ephemeral Ingestion and Session Scoping vs. Persistent Disk Storage
- **Context:** Storing uploaded files indefinitely creates storage bloat and data privacy risks.
- **Decision:** Ingest documents directly into MongoDB Atlas Vector Search tagged by `chat_id`, unlinking (deleting) the file from local disk immediately after chunking.
- **Justification:** Guarantees zero disk residue for compliance (GDPR/HIPAA), provides strict multi-tenant session isolation, and avoids recurring storage maintenance.

---

## Part 2: Problem Statement 1 Reasoning Challenges

### 1. Chunking Strategy Rationale
- **Strategy:** Recursive character splitting (`chunk_size = 800`, `chunk_overlap = 100`).
- **Rationale:** 800 characters (~120-160 words) matches natural paragraph units in technical documents. Chunks larger than 1,200 characters dilute embeddings; chunks smaller than 400 lose context. A 100-character overlap prevents sentences and equations from being cut at chunk boundaries.

### 2. Embedding Model Selection Rationale
- **Selection:** `jina-embeddings-v3` (1024 dimensions).
- **Rationale:** 1024 dimensions offer higher semantic resolution than 384-d models (e.g. MiniLM) without the resource cost of 1536-d models. Native task adapters (`retrieval.query`, `retrieval.passage`) align asymmetric search spaces and support multilingual documents.

### 3. Relevance Determination Mechanism
- **Mechanism:** Pairwise cross-encoder score thresholding ($\tau = 0.02$) with top-k rank ordering.
- **Rationale:** Jina Reranker v2 outputs a relevance score between 0.0 and 1.0. A calibrated 0.02 floor filters out non-matching background text while preserving dense bullet points or figures that might otherwise get dropped.

### 4. Retrieval Errors and Mitigations
- **Vocabulary Mismatch:** Colloquial queries fail against academic prose. *Mitigation:* ReAct autonomous query expansion.
- **Boundary Severing:** Key formulas split across chunks. *Mitigation:* 100-character overlap with recursive boundary fallbacks.
- **Overly Strict Filtering:** High score cutoffs drop valid tables. *Mitigation:* Calibrated noise floor at 0.02.

### 5. Hallucination Reduction Strategies
- **Strict Grounding Prompt:** Model is instructed to base answers strictly on retrieved excerpts and state when facts are missing.
- **Mandatory Inline Citations:** Every factual assertion must cite file name and page number (e.g. `[Gen AI Notes.pdf, Page 8]`).
- **Low Temperature:** Clamped to `0.2` to minimize stochastic sampling.
- **Active Refusal:** Safely declines out-of-scope inquiries and summarizes available document topics.

### 6. Alternative Retrieval Comparison

| Architecture | Latency | Precision on Complex Queries | Key Limitation |
| :--- | :--- | :--- | :--- |
| **BM25 Lexical** | <15 ms | Low | Fails when user wording differs from document text. |
| **Naive Vector Search** | 30-80 ms | Moderate | Semantic drift; includes distantly related chunks. |
| **Hybrid (BM25 + Vector)** | 60-120 ms | Good | Still lacks deep cross-token attention. |
| **Two-Stage Reranked (QADoc)** | 150-250 ms | High | Balanced: broad initial recall refined by cross-encoder. |

### 7. Handling Duplicate and Conflicting Information
- **Duplicates:** The cross-encoder ranks identical passages together; the LLM consolidates them into a single summary citing all relevant pages.
- **Conflicts:** If two documents disagree, the system prompt directs the agent to explicitly state the conflict and cite both sources rather than guessing.
