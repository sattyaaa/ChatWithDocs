# Sample Evaluation Queries

This document lists the test queries used to evaluate the QADoc retrieval and question-answering system against the sample documents:
1. `sample_docs/Gen AI Notes.pdf` (60 pages)
2. `sample_docs/MachineTranslationwithAttention.pdf` (10 pages)

---

## 1. Grounded In-Domain Technical Queries

### Query 1: Generative vs Discriminative AI
- **Question:** "What are the core differences between Generative AI and Discriminative AI?"
- **Target File:** `sample_docs/Gen AI Notes.pdf` (Pages 4, 8)
- **Expected Verification:** Contrast task-specific discriminative models (classification, regression) with general-purpose generative models (text, images, audio), citing training objectives and flexibility.

### Query 2: Transformer Architecture Components
- **Question:** "Briefly explain the transformer architecture and its main components."
- **Target File:** `sample_docs/Gen AI Notes.pdf` (Pages 10, 11)
- **Expected Verification:** Encoder-decoder blocks, self-attention mechanisms, feed-forward layers, and positional encodings.

### Query 3: Fine-Tuning vs RAG
- **Question:** "What is the difference between fine-tuning and RAG?"
- **Target File:** `sample_docs/Gen AI Notes.pdf` (Pages 9, 47, 53)
- **Expected Verification:** Structured comparison across compute cost, knowledge update frequency, dynamic external knowledge vs model weight adaptation, and hallucination reduction.

### Query 4: Temperature in Token Sampling
- **Question:** "What is temperature in token sampling?"
- **Target File:** `sample_docs/Gen AI Notes.pdf` (Page 25)
- **Expected Verification:** Softmax logit scaling formula, difference between low temperature (<1, deterministic/focused) and high temperature (>1, creative/random).

### Query 5: Prompt Engineering Techniques
- **Question:** "What are common prompt engineering techniques mentioned in the notes?"
- **Target File:** `sample_docs/Gen AI Notes.pdf` (Pages 44-46)
- **Expected Verification:** Prompt templates, few-shot prompting, chain-of-thought (CoT), and system prompts.

### Query 6: Role of Attention in Neural Machine Translation
- **Question:** "What is the role of the attention mechanism in neural machine translation? in short"
- **Target File:** `sample_docs/MachineTranslationwithAttention.pdf` (Pages 3, 4)
- **Expected Verification:** Overcoming the fixed-length context vector bottleneck in standard encoder-decoder RNNs, dynamic alignment between decoder steps and all encoder hidden states.

### Query 7: Translation Model Training Dataset
- **Question:** "What dataset was used for training the translation models? in short"
- **Target File:** `sample_docs/MachineTranslationwithAttention.pdf` (Page 5)
- **Expected Verification:** Spanish-English parallel corpus consisting of roughly 1 million sentence pairs.

---

## 2. Out-of-Scope Queries (Testing Safe Refusal)

### Refusal Query 1: Corporate Financial Earnings
- **Question:** "What were the quarterly revenue earnings of Tesla in Q3 2024?"
- **Expected Behavior:** System identifies that Tesla financial reports are absent from the uploaded documents, states what topics are available in `Gen AI Notes.pdf` and `MachineTranslationwithAttention.pdf`, and avoids guessing.

### Refusal Query 2: Medical / Clinical Inquiries
- **Question:** "What are the clinical symptoms of Lyme disease?"
- **Expected Behavior:** Cross-encoder scores fail relevance thresholding; agent clearly refuses, indicates that clinical symptoms of Lyme disease are not found in the uploaded documents, and offers to discuss Generative AI or machine translation topics instead.
