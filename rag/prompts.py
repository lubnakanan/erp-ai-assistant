"""
Prompt construction for the ERP Assistant RAG flow.
"""

SYSTEM_INSTRUCTIONS = """You are ERP Assistant, a helpful expert on ERP systems \
(Accounting, Buying, Selling, Stock, and HR & Payroll), based on official \
ERPNext and Frappe HR documentation.

Rules:
- Answer ONLY using the CONTEXT provided below. Do not use outside knowledge.
- If the context does not contain enough information to answer, say so \
honestly instead of guessing.
- Keep answers concise and practical, as if explaining to a colleague.
- When useful, mention which module (e.g. Accounting, Buying, Selling, \
Stock, HR) the answer relates to.
"""


def format_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        heading = f" — {chunk['heading']}" if chunk.get("heading") else ""
        parts.append(
            f"[Source {i}] Module: {chunk['module']} | {chunk['title']}{heading}\n{chunk['text']}"
        )
    return "\n\n".join(parts)


def build_prompt(question: str, chunks: list[dict]) -> str:
    context = format_context(chunks)
    return f"""{SYSTEM_INSTRUCTIONS}

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""
