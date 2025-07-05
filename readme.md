# 博幼規章寶 LINE Bot

一款針對博幼基金會設計的規章智慧問答機器人，提供規章查詢、圖片辨識、使用教學與互動小測驗功能。

---

## 專案功能

- **規章查詢**：整合 RAG (Retrieval-Augmented Generation)，根據歷史對話與規章文檔自動回答。
- **規章小測驗**：GPT 自動出題並支援 Quick Reply 作答互動。
- **圖片上傳**：可支援未來 OCR 辨識（預留功能）。
- **歷史查詢記錄**：支援上下文記憶（使用 Firebase 實作）。
- **教學與常見問題**：Flex Message 呈現常見問題與教學選單。

---

## 專案架構

```bash
.
├── main.py                     # 主程式入口，處理 webhook 與 LINE 事件
├── generate.py                 # 規章小測驗 GPT 出題模組
├── rag_module.py               # LangChain + Chroma + HuggingFace 向量檢索
├── firebase_service_key.json   # Firebase 服務憑證（請勿上傳）
├── Donation-charter.txt        # 捐款章程原文
├── Integrity-norm.txt          # 誠信規範原文
├── requirements.txt            # 相依套件
├── .gitignore
└── README.md
