# ERP Assistant — AI-Powered Q&A for Core ERP Modules

> A Retrieval-Augmented Generation (RAG) assistant that answers questions about
> the ERP modules most in demand across the Jordanian and Gulf job market —
> Accounting, Buying, Selling, Stock, and HR & Payroll — grounded in real,
> official ERP documentation.

**Live demo:** _(coming soon)_
**Author:** Lubna — [LinkedIn](#) · [Portfolio](#)

---

## 📌 Problem Statement

Employees and job-seekers working with ERP systems (SAP, ERPNext, Odoo, and
similar platforms) constantly need quick, accurate answers to functional
questions — *"What's the difference between a Purchase Receipt and a Purchase
Invoice?"*, *"How do I set up a multi-level leave approval workflow?"* —
without digging through hundreds of pages of documentation.

**ERP Assistant** is a chatbot that retrieves the most relevant passages from
official ERP documentation and uses a language model to generate a grounded,
sourced answer — instead of relying on the model's own (often outdated or
hallucinated) knowledge.

The knowledge base is deliberately scoped to the modules that map most
directly onto core SAP modules widely used by large employers in the region:

| ERP Assistant module | Equivalent SAP module |
|---|---|
| Accounting | FI / CO |
| Buying | MM (Procurement) |
| Stock | MM (Inventory) |
| Selling | SD |
| HR & Payroll | HCM |

## 🏗️ Architecture

```
             ┌─────────────┐
User Query → │  Streamlit  │
             │     UI      │
             └──────┬──────┘
                    │
             ┌──────▼──────┐
             │  RAG Flow   │
             │ (rag/)      │
             └──────┬──────┘
          ┌─────────┼─────────┐
   ┌──────▼─────┐ ┌─▼────────┐│
   │  minsearch  │ │  Chroma  ││  ← hybrid retrieval
   │ (keyword)   │ │ (vector) ││
   └─────────────┘ └──────────┘│
                    ┌───────────▼───────────┐
                    │   Ollama (llama3.2:1b) │  ← local, free LLM
                    └───────────────────────┘
                    ┌───────────────────────┐
                    │  SQLite (logs/feedback)│ → Monitoring charts
                    └───────────────────────┘
```

_(diagram will be refined into a proper image once the flow is finalized)_

🧰 Tech Stack
Layer	Tool	Notes
LLM	Ollama (llama3.2:1b)	Fully local & free; swappable for a cloud API in deployment
Embeddings	sentence-transformers (all-MiniLM-L6-v2)	Lightweight, free, local
Keyword search	minsearch	From the LLM Zoomcamp course
Vector search	Chroma (embedded)	No separate server needed
Ranking	Reciprocal Rank Fusion (RRF)	Combines keyword and vector retrieval results
Storage / logs	SQLite	Query logs + user feedback
UI	Streamlit	Chat interface + monitoring dashboard
Data source	ERPNext Docs & Frappe HR Docs	Official, public documentation
📚 Knowledge Base

The knowledge base is built from official ERPNext and Frappe HR documentation.

Current project scale:

466 documentation pages
4,208 text chunks
Persistent Chroma vector index
Local embeddings using all-MiniLM-L6-v2

The documentation is ingested, processed, chunked, embedded, and indexed before
being used by the RAG pipeline.

🔎 Retrieval Pipeline

The retrieval flow combines two complementary approaches:

Keyword retrieval using minsearch
Vector retrieval using Chroma and all-MiniLM-L6-v2
Reciprocal Rank Fusion (RRF) to combine the retrieved results
The final context is passed to the local LLM
The generated answer is returned with its retrieved sources

This allows the system to benefit from both lexical matching and semantic
similarity.

📊 Monitoring & Feedback

The application includes a dedicated Monitoring tab.

Each interaction can be logged with:

Timestamp
User question
Generated answer
ERP module filter
Response time
Number of retrieved sources
User feedback

The monitoring dashboard includes:

Questions Over Time
Questions by ERP Module
Average Response Time by Module
User Feedback Distribution
Sources Retrieved per Interaction

Users can provide feedback on generated answers using 👍 / 👎.

✅ Project Status (LLM Zoomcamp Capstone Checklist)
 Problem description
 Data ingestion pipeline
 Retrieval flow (knowledge base + LLM)
 Retrieval evaluation
 LLM evaluation
 User interface
 Monitoring & feedback collection
 Reproducibility instructions
 Full containerization (docker-compose)
 Bonus: advanced reranking / query rewriting / cloud deployment
🚀 Getting Started
Prerequisites
Python 3.11+
Ollama
Git
1. Clone the repository
git clone https://github.com/lubnakanan/erp-ai-assistant.git
cd erp-ai-assistant
2. Create and activate a virtual environment

Windows:

python -m venv venv
venv\Scripts\activate

Linux / macOS:

python3 -m venv venv
source venv/bin/activate
3. Install dependencies
pip install -r requirements.txt
4. Pull the required Ollama model

Make sure Ollama is installed and running:

ollama pull llama3.2:1b
5. Run the application
streamlit run app/streamlit_app.py

The application will be available at:

http://localhost:8501
📂 Project Structure
erp-ai-assistant/
├── ingest/          # Data collection & preprocessing
├── rag/             # Retrieval + LLM orchestration
├── evaluation/      # Retrieval & answer quality evaluation
├── app/             # Streamlit application
├── monitoring/      # Feedback logging & dashboard logic
├── data/             # Indexed data and application logs
├── docs/             # Diagrams & supplementary docs
├── tests/            # Unit tests
├── requirements.txt  # Python dependencies
└── README.md         # Project documentation

🔮 Future Work
Docker / Docker Compose: Containerize the application for easier
deployment and reproducibility.
Advanced reranking: Add a dedicated reranking model to improve retrieval
precision.
Query rewriting: Rewrite or expand user queries before retrieval.
Cloud deployment: Support cloud-hosted LLMs and production deployment.
Additional ERP modules: Expand the knowledge base with more ERP domains
and documentation sources.
Agentic workflows: Enable the assistant to perform ERP-related actions
rather than only answering questions.
Authentication and multi-user support: Add access control and user
management for production environments.

⚠️ Limitations
The current system uses a small local LLM (llama3.2:1b) to keep the project
lightweight and free to run locally.
Response latency depends on local CPU and available hardware resources.
The current assistant is primarily a question-answering and retrieval system
and does not directly modify ERP records or execute ERP transactions.
📄 License

MIT — see LICENSE.
