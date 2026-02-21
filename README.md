# VANESSA
### Versatile AI Navigator for Enhanced Semantic Search &amp; Automation

VANESSA is an open-source personal AI assistant designed to orchestrate Large Language Models, perform semantic search via Retrieval-Augmented Generation (RAG), and automate complex workflows.
The system is containerized, modular, and fully extensible — ideal for developers exploring multi-component LLM architectures.

🚀 Key Features

- Modular microservice architecture using Docker (frontend, backend, vector store, database).
- Python/Flask backend with clean separation between API endpoints and LLM orchestration logic.
- RAG pipeline with semantic search backed by an open-source vector database (e.g., Weaviate).
- OpenAI-compatible orchestration layer built with LangChain / LlamaIndex (or custom modules).
- Frontend-agnostic API, ready for React, Vue, Svelte, or plain HTML/JS.
- Fully open source, welcoming contributions and improvements.

🧩 Architecture Overview

+--------------------+       +----------------------+
|     Frontend       | <---> |       Flask API      |
|   (Container #1)   |       |  (Container #2)      |
+--------------------+       +----------+-----------+
                                          |
                                          v
                           +------------------------------+
                           |   LLM Orchestration Engine   |
                           |     (LangChain / Custom)     |
                           +---------------+--------------+
                                           |
                                           v
              +-----------------------------------------------+
              |  Vector Store (Weaviate) — Container #3        |
              |  Persistent semantic index for RAG             |
              +----------------------+-------------------------+
                                     |
                                     v
                         +------------------------+
                         |   Database (optional)  |
                         |   PostgreSQL / Mongo   |
                         |   Container #4         |
                         +------------------------+

📦 Tech Stack

- Backend: Python 3.10+, Flask, LangChain
- Vector Store: Weaviate (self-hosted, persistent)
- Database: PostgreSQL or MongoDB (optional)
- Orchestration: Docker + Docker Compose
- Frontend: TBD (any SPA or static site)
- Dev Tools: VS Code + GitHub + Codex plugin

🧪 Development Mode

- You can develop incrementally without launching all containers:
- Run Flask backend directly in VS Code for fast debugging.
- Mock LLM responses locally for unit tests.
- Only build full stack with Docker Compose when integrating.

📄 Project Goals

- Provide an extensible base for LLM-powered assistants.
- Serve as a high-quality, documented reference for RAG systems.
- Enable automation workflows using natural language.
- Foster open-source collaboration in AI architecture.

🤝 Contributing

VANESSA is open to contributions!
Feel free to open issues, create PRs, or propose new architectural modules.

📜 License

MIT License — free to use, modify, and redistribute.
