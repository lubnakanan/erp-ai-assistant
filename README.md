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

## 🧰 Tech Stack

| Layer | Tool | Notes |
|---|---|---|
| LLM | Ollama (`llama3.2:1b`) | Fully local & free; swappable for a cloud API in deployment |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) | Lightweight, free, local |
| Keyword search | `minsearch` | From the LLM Zoomcamp course |
| Vector search | `Chroma` (embedded) | No separate server needed |
| Storage / logs | SQLite | Query logs + user feedback |
| UI | Streamlit | Chat interface + monitoring dashboard |
| Containerization | Docker / docker-compose | Fully reproducible setup |
| Data source | [ERPNext Docs](https://docs.frappe.io/erpnext/) & [Frappe HR Docs](https://docs.frappe.io/hr/) | Official, public documentation |

## ✅ Project Status (LLM Zoomcamp Capstone Checklist)

- [x] Problem description
- [ ] Data ingestion pipeline
- [ ] Retrieval flow (knowledge base + LLM)
- [ ] Retrieval evaluation (multiple approaches compared)
- [ ] LLM evaluation (multiple approaches compared)
- [ ] User interface
- [ ] Monitoring & feedback collection
- [ ] Full containerization (docker-compose)
- [ ] Reproducibility instructions
- [ ] Bonus: hybrid search / reranking / cloud deployment

## 🚀 Getting Started

_(setup instructions will be added as each component is completed)_

## 📂 Project Structure

```
erp-ai-assistant/
├── ingest/         # Data collection & preprocessing
├── rag/            # Retrieval + LLM orchestration
├── evaluation/      # Retrieval & answer quality evaluation
├── app/            # Streamlit application
├── monitoring/     # Feedback logging & dashboard logic
├── data/           # Scraped documentation (regenerated via ingest script)
├── docs/           # Diagrams & supplementary docs
└── tests/          # Unit tests
```

## 📄 License

MIT — see [LICENSE](LICENSE).
