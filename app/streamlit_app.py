"""
ERP Assistant — Streamlit chat interface.

Visual style: inspired by SAP GUI / SAP Fiori (deep blue header bar,
SAP's signature blue accent, clean corporate look) — a deliberate
design choice tying the app back to the SAP modules it mirrors
(Accounting/FI, Buying+Stock/MM, Selling/SD, HR/HCM).

Run with:
    streamlit run streamlit_app.py
(from inside the app/ folder, with the venv activated)
"""

import sys
import time
from pathlib import Path

import streamlit as st

# Let this file import from the sibling rag/ folder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rag"))
from rag_flow import answer_question  # noqa: E402

# Import monitoring / SQLite logging
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "monitoring"))
from db import init_db, log_interaction, update_feedback  # noqa: E402


MODULES = ["All modules", "Accounting", "Buying", "Selling", "Stock", "HR"]

# Initialize the monitoring database
init_db()

st.set_page_config(
    page_title="ERP Assistant",
    page_icon="🗂️",
    layout="centered",
)

# ---------------------------------------------------------------------------
# SAP-inspired styling
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --sap-blue-dark: #0F1823;
        --sap-blue: #2E9BFF;
        --sap-blue-light: rgba(46, 155, 255, 0.12);
        --sap-grey: #151E2B;
        --sap-text: #F5F6F7;
    }

    .stApp {
        background-color: var(--sap-grey);
    }

    .sap-titlebar {
        background-color: var(--sap-blue-dark);
        color: white;
        padding: 10px 18px;
        border-radius: 4px 4px 0 0;
        font-family: Arial, "Segoe UI", sans-serif;
        font-size: 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0;
        border: 1px solid #2A3B4D;
        border-bottom: none;
    }

    .sap-titlebar .app-name {
        font-weight: 600;
        letter-spacing: 0.3px;
    }

    .sap-titlebar .sys-info {
        font-size: 12px;
        color: #8FA6BD;
    }

    .sap-subbar {
        background-color: var(--sap-blue);
        color: #05121F;
        font-weight: 500;
        padding: 6px 18px;
        font-family: Arial, "Segoe UI", sans-serif;
        font-size: 12.5px;
        border-radius: 0 0 4px 4px;
        margin-bottom: 18px;
    }

    .stChatMessage {
        font-family: Arial, "Segoe UI", sans-serif;
    }

    div[data-testid="stChatMessageContent"] {
        border-radius: 6px;
    }

    .sap-source {
        background-color: var(--sap-blue-light);
        border-left: 3px solid var(--sap-blue);
        padding: 6px 10px;
        margin-top: 4px;
        font-size: 12.5px;
        border-radius: 3px;
        color: var(--sap-text);
    }

    .sap-source a {
        color: #6CBBFF;
    }

    .feedback-label {
        font-size: 12px;
        color: #8FA6BD;
        margin-top: 8px;
        margin-bottom: 2px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="sap-titlebar">
        <span class="app-name">🗂️ ERP Assistant</span>
        <span class="sys-info">System: EAA &nbsp;|&nbsp; Client: 100 &nbsp;|&nbsp; User: LUBNA</span>
    </div>

    <div class="sap-subbar">
        RAG-powered Q&amp;A over Accounting (FI/CO) · Buying &amp; Stock (MM) · Selling (SD) · HR &amp; Payroll (HCM)
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Filters")

    selected_module = st.selectbox(
        "Restrict search to module",
        MODULES,
    )

    st.markdown("---")

    st.markdown(
        "**About**\n\n"
        "ERP Assistant answers questions about core ERP modules "
        "(the ones most commonly used across SAP implementations: "
        "FI/CO, MM, SD, HCM) using retrieval-augmented generation "
        "over official ERPNext & Frappe HR documentation.\n\n"
        "Runs fully locally & free — Ollama (`llama3.2:1b`) + Chroma."
    )

    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.rerun()

# ---------------------------------------------------------------------------
# Chat state
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------------------------------------------
# Feedback helper
# ---------------------------------------------------------------------------
def show_feedback(msg):
    """Display and save thumbs-up / thumbs-down feedback."""

    log_id = msg.get("log_id")

    if not log_id:
        return

    current_feedback = msg.get("feedback")

    if current_feedback == "up":
        st.caption("👍 Thanks for your feedback!")
        return

    if current_feedback == "down":
        st.caption("👎 Thanks for your feedback!")
        return

    st.markdown(
        '<div class="feedback-label">Was this answer helpful?</div>',
        unsafe_allow_html=True,
    )

    col1, col2, _ = st.columns([1, 1, 8])

    with col1:
        if st.button("👍", key=f"feedback_up_{log_id}"):
            update_feedback(log_id, "up")
            msg["feedback"] = "up"
            st.rerun()

    with col2:
        if st.button("👎", key=f"feedback_down_{log_id}"):
            update_feedback(log_id, "down")
            msg["feedback"] = "down"
            st.rerun()


# ---------------------------------------------------------------------------
# Display previous conversation
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant":

            if msg.get("sources"):
                with st.expander("📎 Sources"):
                    for s in msg["sources"]:
                        st.markdown(
                            f'<div class="sap-source">[{s["module"]}] '
                            f'<a href="{s["url"]}" target="_blank">{s["title"]}</a></div>',
                            unsafe_allow_html=True,
                        )

            st.caption(
                f"⏱️ {msg.get('response_time_sec', '?')}s"
            )

            show_feedback(msg)


# ---------------------------------------------------------------------------
# New question
# ---------------------------------------------------------------------------
question = st.chat_input(
    "Ask about Accounting, Buying, Selling, Stock, or HR..."
)

if question:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):

        with st.spinner("Looking through ERP documentation..."):

            module_filter = (
                None
                if selected_module == "All modules"
                else selected_module
            )

            result = answer_question(
                question,
                module=module_filter,
            )

        st.markdown(result["answer"])

        if result["sources"]:
            with st.expander("📎 Sources"):
                for s in result["sources"]:
                    st.markdown(
                        f'<div class="sap-source">[{s["module"]}] '
                        f'<a href="{s["url"]}" target="_blank">{s["title"]}</a></div>',
                        unsafe_allow_html=True,
                    )

        st.caption(
            f"⏱️ {result['response_time_sec']}s"
        )

        # ---------------------------------------------------------------
        # Log interaction
        # ---------------------------------------------------------------
        log_id = log_interaction(
            question=question,
            answer=result["answer"],
            module_filter=module_filter,
            response_time_sec=result["response_time_sec"],
            num_sources=len(result["sources"]),
        )

        # Create the message object before displaying feedback
        assistant_message = {
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
            "response_time_sec": result["response_time_sec"],
            "log_id": log_id,
            "feedback": None,
        }

        st.session_state.messages.append(assistant_message)

        # ---------------------------------------------------------------
        # Feedback for the newly generated answer
        # ---------------------------------------------------------------
        show_feedback(assistant_message)