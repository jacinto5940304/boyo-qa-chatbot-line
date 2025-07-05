
# Boyo Foundation Regulation QA Chatbot (LINE Bot)

This project is a regulation Q&A chatbot designed for the Boyo Social Welfare Foundation. It integrates Retrieval-Augmented Generation (RAG), GPT-4o, Firebase, and the LINE Messaging API to provide instant answers to regulatory questions. It also features an interactive multiple-choice quiz system and support for persistent user conversation history.

---

## Features

- **Regulation Q&A via RAG**  
  Retrieves relevant regulation excerpts and uses a hybrid LLM pipeline (LangChain + GPT-4o) to answer user queries in natural language.

- **Automatic Quiz Generation**  
  Automatically generates single-choice quiz questions from regulation texts using GPT-4o and delivers them via LINE Quick Reply buttons.

- **Persistent User Memory**  
  Stores recent conversation history in Firebase Realtime Database to support context-aware responses.

- **Predefined FAQ and Tutorials**  
  Includes a Flex Message-based interface for displaying frequently asked questions and user tutorials.

- **Modular RAG Backend**  
  Supports ChromaDB-based document retrieval with HuggingFace embeddings, downloaded and indexed from Drive-hosted .txt regulation files.

---

## System Architecture

```bash
.
├── main.py                     # Main entry point (Flask + LINE Webhook)
├── generate.py                 # GPT-powered quiz question generator
├── rag_module.py               # RAG pipeline (LangChain + Chroma + HuggingFace + OpenAI)
├── firebase_service_key.json   # Firebase service credentials (excluded from version control)
├── Donation-charter.txt        # Regulation: Donation-related guidelines
├── Integrity-norm.txt          # Regulation: Integrity norms
├── requirements.txt            # Project dependencies
├── .gitignore
└── README.md
```

---

## Tech Stack

| Category | Tools / Libraries |
|---------|-------------------|
| Messaging API | LINE Messaging API v3 |
| Backend | Python, Flask, Firebase Admin SDK |
| LLM Integration | OpenAI GPT-4o, LangChain |
| Retrieval System | ChromaDB, HuggingFace Embeddings (`all-MiniLM-L6-v2`) |
| Deployment | Cloud Run or any WSGI-compatible server |
| Quiz Logic | GPT-generated multiple-choice with validation and Firebase tracking |

---

## Setup & Deployment

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Secrets

Create a `config.py` file with the following variables:

```python
ACCESS_TOKEN = "your_line_channel_access_token"
CHANNEL_SECRET = "your_line_channel_secret"
OPENAI_API_KEY = "your_openai_api_key"
HF_TOKEN = "your_huggingface_token"
FIREBASE_URL = "your_firebase_database_url"
FAQ_FLEX_JSON = {...}  # Flex message content for FAQ
FAQ_ANSWERS = {...}    # Static answers for common questions
TUTORIAL_CAROUSEL = {...}  # Flex carousel for tutorial images
```

Place the `firebase_service_key.json` in the root directory (do not commit it to GitHub).

### 3. Run the Server

```bash
python main.py
```

---

## RAG Retrieval Pipeline (rag_module.py)

- Loads `.txt` files from the `./data` directory or Google Drive via `gdown`
- Embeds regulation sentences using HuggingFace
- Indexes them with Chroma vector store
- Retrieves top-3 relevant segments for each query
- Feeds retrieved context into GPT-4o to generate an accurate response

---

## Quiz Generation Logic (generate.py)

- Uses GPT-4o-mini to generate a new regulation-based multiple-choice question
- Avoids duplication by referencing Firebase quiz history
- Returns `question`, `options`, and `answer`, and pushes them to LINE using Quick Reply buttons

---

## Licensing & Credits

This project was developed by a student team at National Tsing Hua University for the Boyo Foundation. Open-source components used under respective licenses.


## Line bot link
[加入博幼QA機器人](https://lin.ee/zl9FBN7)
