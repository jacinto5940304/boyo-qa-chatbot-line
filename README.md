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

- **Travel Planning Guide**  
  Provides comprehensive 7-day Shanghai + Nanjing family trip planning, including attractions, food, shopping, bars, and transportation information. Automatically responds to travel-related queries.

- **Modular RAG Backend**  
  Supports ChromaDB-based document retrieval with HuggingFace embeddings, downloaded and indexed from Drive-hosted .txt regulation files.

---

## System Architecture

```bash
.
├── main.py                              # Main entry point (Flask + LINE Webhook)
├── generate.py                          # GPT-powered quiz question generator
├── rag_module.py                        # RAG pipeline (LangChain + Chroma + HuggingFace + OpenAI)
├── firebase_service_key.json            # Firebase service credentials (excluded from version control)
├── Donation-charter.txt                 # Regulation: Donation-related guidelines
├── Integrity-norm.txt                   # Regulation: Integrity norms
├── Shanghai-Nanjing-Travel-Guide.txt    # Travel guide content for chatbot responses
├── Shanghai-Nanjing-7Day-Presentation.md # Presentation-style travel guide
├── requirements.txt                     # Project dependencies
├── .gitignore
└── README.md
```
![image](https://github.com/user-attachments/assets/8a5918f7-257f-4f3a-bb3b-296bb037cffc)



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

## Travel Planning Guide

The chatbot now includes a comprehensive 7-day Shanghai + Nanjing family trip planning feature:

### Features
- **Automatic Detection**: Responds when users ask about Shanghai, Nanjing, or travel-related queries
- **AI-Powered Responses**: Uses GPT-4o-mini to extract relevant information from the travel guide based on user questions
- **Comprehensive Content**: Includes attractions, food recommendations, shopping areas, bars, and transportation details
- **Two Formats Available**:
  - `Shanghai-Nanjing-Travel-Guide.txt`: Detailed text-based guide for chatbot responses
  - `Shanghai-Nanjing-7Day-Presentation.md`: Presentation-style markdown format

### Coverage
- **Day 1-3**: Shanghai (The Bund, Oriental Pearl Tower, Xintiandi, Museums)
- **Day 4**: Transit to Nanjing + Qinhuai River night tour
- **Day 5-6**: Nanjing (Sun Yat-sen Mausoleum, Ming Xiaoling, Presidential Palace, Museums)
- **Day 7**: Return journey
- **Additional Info**: Transportation methods, budget planning, accommodation recommendations, shopping guides

### Usage Example
Users can ask questions like:
- "上海南京七日遊" (Shanghai-Nanjing 7-day trip)
- "上海有什麼景點" (What attractions are in Shanghai)
- "南京美食推薦" (Nanjing food recommendations)

The chatbot will intelligently extract relevant information from the travel guide and provide customized responses.

---

## Licensing & Credits

This project was developed by a student team at National Tsing Hua University for the Boyo Foundation. Open-source components used under respective licenses.


## Line bot link
[加入博幼QA機器人](https://lin.ee/zl9FBN7)


## 
[DEMO](https://youtu.be/i60KQOyVMrA?si=dwp1VXn0yGG4ISu5)

