"""
ERP Assistant — Streamlit chat interface + monitoring dashboard.

Visual style: inspired by SAP GUI / SAP Fiori.

Run with:
    streamlit run streamlit_app.py
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "rag"))
from rag_flow import answer_question  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "monitoring"))
from db import init_db, log_interaction, update_feedback, get_all_logs  # noqa: E402


MODULES = [
    "All modules",
    "Accounting",
    "Buying",
    "Selling",
    "Stock",
    "HR",
]

# Initialize monitoring database
init_db()

st.set_page_config(
    page_title="ERP Assistant",
    page_icon="🗂️",
    layout="wide",
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

    .monitor-title {
        font-family: Arial, "Segoe UI", sans-serif;
        font-size: 24px;
        font-weight: 600;
        margin-bottom: 4px;
    }

    .monitor-subtitle {
        color: #8FA6BD;
        font-size: 13px;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
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
# Session state
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


# ===========================================================================
# TABS
# ===========================================================================

chat_tab, monitoring_tab = st.tabs(
    ["💬 ERP Assistant", "📊 Monitoring"]
)


# ===========================================================================
# CHAT TAB
# ===========================================================================
with chat_tab:

    # -----------------------------------------------------------------------
    # Display previous conversation
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # New question
    # -----------------------------------------------------------------------
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
            # Feedback
            # ---------------------------------------------------------------
            show_feedback(assistant_message)


# ===========================================================================
# MONITORING TAB
# ===========================================================================
with monitoring_tab:

    st.markdown(
        '<div class="monitor-title">📊 Monitoring Dashboard</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="monitor-subtitle">'
        "Track usage, response performance, retrieval sources, and user feedback."
        "</div>",
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------------------------
    # Load logs
    # -----------------------------------------------------------------------
    logs = get_all_logs()

    if not logs:

        st.info(
            "No interactions have been logged yet. "
            "Use the ERP Assistant tab to ask a question."
        )

    else:

        df = pd.DataFrame(logs)

        # Convert timestamp to datetime
        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            errors="coerce",
        )

        # Ensure numeric columns are numeric
        df["response_time_sec"] = pd.to_numeric(
            df["response_time_sec"],
            errors="coerce",
        )

        df["num_sources"] = pd.to_numeric(
            df["num_sources"],
            errors="coerce",
        )

        # -------------------------------------------------------------------
        # KPI cards
        # -------------------------------------------------------------------
        total_questions = len(df)

        avg_response_time = df["response_time_sec"].mean()

        avg_sources = df["num_sources"].mean()

        feedback_count = df["feedback"].notna().sum()

        positive_feedback = (
            (df["feedback"] == "up").sum()
        )

        satisfaction_rate = (
            positive_feedback / feedback_count * 100
            if feedback_count > 0
            else 0
        )

        k1, k2, k3, k4 = st.columns(4)

        with k1:
            st.metric(
                "Total Questions",
                total_questions,
            )

        with k2:
            st.metric(
                "Avg Response Time",
                f"{avg_response_time:.2f}s",
            )

        with k3:
            st.metric(
                "Avg Sources / Answer",
                f"{avg_sources:.1f}",
            )

        with k4:
            st.metric(
                "Satisfaction",
                f"{satisfaction_rate:.1f}%",
            )

        st.markdown("---")

        # ===================================================================
        # CHART 1 — Questions Over Time
        # ===================================================================
        st.subheader("1. Questions Over Time")

        questions_over_time = (
            df.assign(
                date=df["timestamp"].dt.date
            )
            .groupby("date")
            .size()
            .rename("Questions")
        )

        st.line_chart(
            questions_over_time,
            use_container_width=True,
        )

        # ===================================================================
        # CHART 2 — Questions by Module
        # ===================================================================
        st.subheader("2. Questions by ERP Module")

        module_counts = (
            df["module_filter"]
            .fillna("All modules")
            .value_counts()
            .rename("Questions")
        )

        st.bar_chart(
            module_counts,
            use_container_width=True,
        )

        # ===================================================================
        # CHART 3 — Average Response Time by Module
        # ===================================================================
        st.subheader("3. Average Response Time by Module")

        response_by_module = (
            df.groupby("module_filter")["response_time_sec"]
            .mean()
            .sort_values(ascending=False)
            .rename("Avg Response Time (sec)")
        )

        st.bar_chart(
            response_by_module,
            use_container_width=True,
        )

        # ===================================================================
        # CHART 4 — User Feedback
        # ===================================================================
        st.subheader("4. User Feedback Distribution")

        feedback_counts = (
            df["feedback"]
            .map(
                {
                    "up": "👍 Helpful",
                    "down": "👎 Not Helpful",
                }
            )
            .dropna()
            .value_counts()
            .rename("Responses")
        )

        if len(feedback_counts) > 0:
            st.bar_chart(
                feedback_counts,
                use_container_width=True,
            )
        else:
            st.info(
                "No user feedback has been submitted yet."
            )

        # ===================================================================
        # CHART 5 — Sources per Interaction
        # ===================================================================
        st.subheader("5. Sources Retrieved per Interaction")

        sources_over_time = (
            df.sort_values("id")
            .set_index("id")["num_sources"]
            .rename("Number of Sources")
        )

        st.line_chart(
            sources_over_time,
            use_container_width=True,
        )

        # -------------------------------------------------------------------
        # Recent interactions table
        # -------------------------------------------------------------------
        st.subheader("Recent Interactions")

        display_columns = [
            "id",
            "timestamp",
            "question",
            "module_filter",
            "response_time_sec",
            "num_sources",
            "feedback",
        ]

        recent_df = (
            df[display_columns]
            .sort_values("id", ascending=False)
            .head(10)
            .copy()
        )

        recent_df["feedback"] = recent_df["feedback"].map(
            {
                "up": "👍",
                "down": "👎",
            }
        )

        recent_df = recent_df.rename(
            columns={
                "id": "ID",
                "timestamp": "Timestamp",
                "question": "Question",
                "module_filter": "Module",
                "response_time_sec": "Response Time (s)",
                "num_sources": "Sources",
                "feedback": "Feedback",
            }
        )

        st.dataframe(
            recent_df,
            use_container_width=True,
            hide_index=True,
        )