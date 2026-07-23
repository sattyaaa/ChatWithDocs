from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from rag.config import llm
from rag.retrieval import retrieve_documents

import logging
logger = logging.getLogger(__name__)


# System Prompt

SYSTEM_PROMPT = """
You are a helpful AI assistant for question answering.

Use ONLY the provided context to answer the user's question.

If the answer cannot be found in the context, reply:
"I couldn't find the answer in the uploaded documents."

Keep your answers:
- Accurate
- Concise
- Well-structured

Context:
{context}
""".strip()



def _build_prompt() ->ChatPromptTemplate:
    """
    Create the prompt template for the RAG pipeline

    Returns:
        A ChatPromptTemplate instance.
    """

    return ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{question}"),
    ])

    

def _formate_context(documents: list[Document]) -> str:
    """
    Formate retrived documents into a single context string.

    Args:
        documents: Retrieved document chunks.

    Returns:
        A single string containing the concatenated document contents.
    """

    return "\n\n".join(
        document.page_content for document in documents
    )



def ask_question(
    query: str, 
    chat_id: str,
    document_ids: list[str] | None = None,
):
    """
    Answers a question using RAG

    Args:
        query: User's question.
        chat_id: Unique identifier for the current chat.
        document_ids: Optiona list of documents IDs to search.

    Returns:
        A dictionary containing:
        - "answer": The generated answer string.
        - "sources": A list of source filenames and chunk IDs.
    """

    try:
        documents = retrieve_documents(
            query=query,
            chat_id=chat_id,
            document_ids=document_ids,
        )

        context = _formate_context(documents)

        rag_chain = (_build_prompt() | llm | StrOutputParser())
        answer = rag_chain.invoke({
            "context" : context,
            "question": query,
        })


        return {
            "answer": answer,
            "sources": documents,
        }

    except Exception as exc:
        logger.exception("Failed to answer question.")
        raise RuntimeError("Failed to generate answer.") from exc




PROMPT = _build_prompt()
RAG_CHAIN = ( PROMPT | llm | StrOutputParser())