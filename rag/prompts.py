"""
Prompt templates for the RAG pipeline.
"""

# Prompt for condensing/rephrasing the question based on chat history
CONDENSE_QUESTION_PROMPT = """
Given the following chat history and a follow-up question, rephrase the follow-up question to be a standalone question that can be searched in a database.
Respond with ONLY the rephrased question. Do not include any explanation, conversational filler, or intro.

Chat History:
{chat_history}

Follow-up Question: {question}
Standalone Question:
""".strip()


# System Prompt for the final Q&A step
SYSTEM_PROMPT = """
You are a helpful AI assistant for question answering.

Use the provided context and conversation history to answer the user's question. Use ONLY the provided context to answer.

If the answer cannot be found in the context, reply:
"I couldn't find the answer in the uploaded documents."

Keep your answers:
- Accurate
- Concise
- Well-structured

Context:
{context}

Conversation History:
{chat_history}
""".strip()
