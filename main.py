# import functions_framework
from flask import Flask, abort, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage, FlexMessage, PushMessageRequest
from linebot.v3.messaging.models import FlexContainer, QuickReply, QuickReplyItem, MessageAction, ImageMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent

import threading
import requests
import os
import time

# Key
from config import ACCESS_TOKEN, CHANNEL_SECRET, OPENAI_API_KEY, FIREBASE_URL, FAQ_FLEX_JSON, FAQ_ANSWERS, TUTORIAL_CAROUSEL

# generate the quiz
from generate import generate_quiz_question, format_options

# RAG
from rag_module import get_response

# Firebase
import json
import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate("firebase_service_key.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_URL
    })

# constant
MAX_HISTORY = 5  # 上下文限制頁數

# read rules 
with open("Donation-charter.txt", encoding="utf-8") as f:
    donation_rules = f.read()

with open("Integrity-norm.txt", encoding="utf-8") as f:
    integrity_rules = f.read()

all_rules = donation_rules + "\n" + integrity_rules

# lineBot Setup
configuration = Configuration(access_token=ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# Flask app for Cloud Run
app = Flask(__name__)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        import logging
        logging.exception(f"[Webhook Crash] {str(e)}")
        abort(500)

    return "OK"


# welcome message
@handler.add(FollowEvent)
def handle_follow(event):
    welcome_text = (
        "👋 歡迎加入博幼規章寶！\n\n"
        "我是你的規章智慧小幫手，幫你快速查詢基金會各項規章制度和工作流程 📚\n\n"
        "你可以這樣使用我：\n"
        "🔍 輸入問題查詢規章（例如：我可以請幾天病假？）\n"
        "📄 查看你過去查詢的紀錄\n"
        "📸 上傳流程紀錄照片（像是文件、現場紀錄）\n"
        "🎓 觀看使用教學與常見問答\n\n"
        "不確定從哪開始？直接輸入問題就對了！\n\n"
        "別緊張，我相信你很快就會上手的。"
    )

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=welcome_text)]
            )
        )

# 使用者訊息處理函數，仍由 LINE SDK 呼叫
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):

    # 開新 thread 處理 GPT
    user_input = event.message.text.strip()
    if user_input == "測驗":
        # 先回覆提示訊息 ✅ 這樣 LINE 收到 reply 會立即顯示
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="✏️ 生成試題中，請稍候...")]
                )
            )
        # 再開 thread 處理 quiz（背景非同步）
        user_id = getattr(event.source, 'user_id', None)
        threading.Thread(target=generate_quiz_and_push, args=(user_id,)).start()
        return
    
    threading.Thread(target=process_gpt_and_push, args=(event,)).start()

def get_memory(user_id):
    ref = db.reference(f"/chat_memory/{user_id}")
    raw_data = ref.get()
    if not raw_data:
        return []
    try:
        # 排序 key（Firebase 的 push key 可排序），轉 list
        sorted_items = sorted(raw_data.items())  # [(key1, {...}), (key2, {...})...]
        return [item[1] for item in sorted_items]  # 取 value list
    except Exception as e:
        import logging
        logging.exception(f"[Memory Parse Error] {str(e)}")
        return []

def append_memory(user_id, user_text, bot_text):
    ref = db.reference(f"/chat_memory/{user_id}")
    ref.push({"user": user_text, "bot": bot_text})

def clear_memory(user_id):
    db.reference(f"/chat_memory/{user_id}").delete()



# welcome messages
def process_gpt_and_push(event):

    total_start = time.time()

    answer = "⚠️ 很抱歉，目前暫時無法取得規章資訊，請稍後再試。"
    user_input = event.message.text.strip()
    user_id = getattr(event.source, 'user_id', None)
    if not user_id:
        import logging
        logging.warning("⚠️ 無法取得 user_id，跳過處理")
        return
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)


#### SPECIAL CASE START ####

        # 若使用者輸入結束，清除記憶
        if user_input == "結束":
            clear_memory(user_id)
            print(f"[DEBUG] 清除chat memory耗時：{time.time() - total_start:.2f} 秒")
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="✅ 已結束本次問題，我不會再記住剛剛的對話內容囉！")]
                )
            )
            print(f"[DEBUG] LINE 推送結束完成，用時：{time.time() - total_start:.2f} 秒")
            return
        if user_input == "繼續":
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="請問還有什麼想要詢問的呢？")]
                )
            )
            print(f"[DEBUG] LINE 推送繼續完成，用時：{time.time() - total_start:.2f} 秒")
            return

        if user_input == "常見問題":
            faq_message = FlexMessage(
                alt_text="📋 常見問題選單",
                contents=FlexContainer.from_dict(FAQ_FLEX_JSON)
            )
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[faq_message]
                )
            )
            print(f"[DEBUG] LINE 推送常見問題完成，用時：{time.time() - total_start:.2f} 秒")
            return
        
        # 若使用者輸入結束測驗，清除測驗記憶
        if user_input == "結束測驗":
            clear_memory(user_id)
            print(f"[DEBUG] 清除quiz history，耗時：{time.time() - total_start:.2f} 秒")
            clear_quiz_history(user_id)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="✅ 測驗已結束，感謝你的作答！")]
                )
            )
            print(f"[DEBUG] LINE 推送結束問題完成，用時：{time.time() - total_start:.2f} 秒")
            return
        
        # 若是常見問題之一，則回覆固定答案
        if user_input in FAQ_ANSWERS:
            answer = FAQ_ANSWERS[user_input]
            append_memory(user_id, user_input, answer)
            print(f"[DEBUG] 寫入firebase常見問題，耗時：{time.time() - total_start:.2f} 秒")

            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=answer)]
                )
            )
            print(f"[DEBUG] LINE 推送常見問題完成，用時：{time.time() - total_start:.2f} 秒")
            return
        
        if user_input == "使用教學":
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        FlexMessage(
                            alt_text="📖 使用教學圖片",
                            contents=FlexContainer.from_dict(TUTORIAL_CAROUSEL)
                        )
                    ]
                )
            )
            print(f"[DEBUG] LINE 推送使用教學完成，用時：{time.time() - total_start:.2f} 秒")
            return


        # if user_input == "測驗":

        #     # Step 1: 立即回應提示訊息（不會失敗）
        #     line_bot_api.reply_message_with_http_info(
        #         ReplyMessageRequest(
        #             reply_token=event.reply_token,
        #             messages=[TextMessage(text="✏️ 生成試題中，請稍候...")]
        #         )
        #     )
        #     # Step 2: 開 thread 非同步生成試題（避免卡在 reply）
        #     threading.Thread(target=generate_quiz_and_push, args=(user_id,)).start()
        #     return

        if user_input in ["A", "B", "C"]:
            quiz_ref = db.reference(f"/quiz/{user_id}/current")
            quiz_data = quiz_ref.get()

            if not quiz_data:
                reply_text = "⚠️ 沒有正在進行的題目喔～請輸入「測驗」開始答題！"
            else:
                correct = quiz_data["answer"].strip().upper()
                if user_input.upper() == correct:
                    reply_text = "✅ 恭喜你答對了！"
                else:
                    reply_text = f"❌ 答錯了，正確答案是 {correct}"
                quiz_ref.delete()
                print(f"[DEBUG] 刪除quiz current，耗時：{time.time() - total_start:.2f} 秒")
                quick_reply = QuickReply(
                    items=[
                        QuickReplyItem(action=MessageAction(label="📘 下一題", text="測驗")),
                        QuickReplyItem(action=MessageAction(label="🛑 結束測驗", text="結束測驗"))
                    ]
                )

            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text, quick_reply=quick_reply)]
                )
            )
            print(f"[DEBUG] LINE 推送揭曉答案完成，用時：{time.time() - total_start:.2f} 秒")
            return

#### SPECIAL CASE END ####


        try:
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="思考中，請稍候...")]
                )
            )
            print(f"[DEBUG] 傳送思考中，耗時：{time.time() - total_start:.2f} 秒")

        except Exception as e:
            import logging
            logging.exception(f"[Push Pre-message Error] {str(e)}")

        # ✅ Step 2: Call RAG (--OpenAI（非同步完成後再送--)
        try:
            # 取過去 N 筆記憶，拼成 context 一併餵給 RAG
            history = get_memory(user_id)[-MAX_HISTORY:]  # 限制取最近的幾則
            print(f"[DEBUG] 取得對話紀錄，耗時：{time.time() - total_start:.2f} 秒")
            history_context = "\n".join([f"User: {item['user']}\nBot: {item['bot']}" for item in history])

            # 拼成完整查詢字串（你朋友的 RAG 會將這整段丟給 GPT）
            full_query = f"{history_context}\n\nUser: {user_input}"

            # 調用 RAG 系統
            res = get_response(full_query)
            print(f"[DEBUG] 調用RAG，耗時：{time.time() - total_start:.2f} 秒")
            
            context_text = "\n".join([doc.page_content for doc in res["context"]])

            # backup : use original GPT
            if "unsure" in res["answer"].lower():
                print("[RAG Miss] 使用 fallback 模式")
                # 改為 all_rules + OpenAI 傳統問法

                prompt = (
                    "你是博幼基金會的規章專家，請根據條文內容與使用者上下文進行回答，請避免捏造內容, 可提供你是參考什麼原文。\n"
                    f"條文如下：\n{all_rules}\n\n對話歷史：\n{history_context}\n\n使用者提問：{user_input}"
                )

                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": "你是博幼基金會規章專家，請根據問題回答相關內容，你知道條文是出自於誠信規章還是捐款條例"},
                            {"role": "user", "content": prompt}
                        ]
                    },
                    timeout=30
                )
                if response.status_code == 200:
                    print(f"[DEBUG] 額外調用GPT，耗時：{time.time() - total_start:.2f} 秒")
                    data = response.json()
                    answer = data["choices"][0]["message"]["content"].strip()

                else:
                    answer = f"伺服器錯誤：{response.status_code}"

            else:
                answer = res["answer"]
                if any(term in res["answer"] for term in [  "條文", "條款", "條項", "法條", "細則",
                                                            "規定", "規範", "規約", "守則", "規矩", "限制", "辦法", "要求", "條件",
                                                            "章節", "段落", "部分", "節次", "子章", "篇章",
                                                            "條例", "法律", "法規", "規則", "準則", "措施", "制度",
                                                            "規章", "章程", "章則", "會章", "組織章程", "規章制度"]):
                    answer += "\n\n🔎 參考條文：\n" + context_text

            if any(term in res["answer"] for term in ["誠信規章", "誠信", "誠信經營規範"]):
                answer += "\n\n🔎 誠信規章原文連結：\n" + "https://drive.google.com/file/d/1NGgZy4wi9Q69YNgTGcxEN0bScwu5Nzo4/view?usp=sharing"

            if any(term in res["answer"] for term in ["捐款條例", "捐款", "捐助章程"]):
                answer += "\n\n🔎 捐款條例原文連結：\n" + "https://drive.google.com/file/d/1foZjFAlnAK9g2sQaBO5yzQ3Lip0LmMMO/view?usp=sharing"
            # 存入記憶
            append_memory(user_id, user_input, answer)
            print(f"[DEBUG] 對話紀錄存入firebase，耗時：{time.time() - total_start:.2f} 秒")
   

        except Exception as e:
            import logging
            logging.exception(f"[RAG GPT Error] {str(e)}")

        try:
            # ✅ Step 3: 推送 Flex card
            flex_json = {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📘 規章查詢結果",
                            "weight": "bold",
                            "size": "lg"
                        },
                        {
                            "type": "text",
                            "text": answer,
                            "wrap": True
                        }
                    ]
                }
            }

            flex_message = FlexMessage(
                alt_text="📘 規章查詢結果",
                contents=FlexContainer.from_dict(flex_json)
            )

            flex_message.quick_reply = QuickReply(
                items=[
                    QuickReplyItem(action=MessageAction(label="✅ 繼續追問", text="繼續")),
                    QuickReplyItem(action=MessageAction(label="🛑 結束問題", text="結束"))
                ]
            )

            line_bot_api.push_message_with_http_info(
                PushMessageRequest(
                    to=user_id,
                    messages=[flex_message]
                )
            )
            print(f"[DEBUG] LINE 推送自然語言回答完成，耗時：{time.time() - total_start:.2f} 秒")
        except Exception as e:
            import logging
            logging.exception(f"[GPT or Flex render Error] {str(e)}")


def generate_quiz_and_push(user_id):
    start = time.time()
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        print(f"[DEBUG] 開始生成 quiz for {user_id}")
        history_ref = db.reference(f"/quiz/{user_id}/history")
        history_data = history_ref.get() or {}
        asked_questions = set(history_data.values())

        q, opt, ans = generate_quiz_question(all_rules, asked_questions)
        print(f"[DEBUG] GPT 回應時間：{time.time() - start:.2f} 秒")
        if not q:
            line_bot_api.push_message_with_http_info(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text="⚠️ 很抱歉，目前無法出題，請稍後再試！")]
                )
            )
            return

        db.reference(f"/quiz/{user_id}/history").push(q)
        db.reference(f"/quiz/{user_id}/current").set({
            "question": q,
            "answer": ans
        })

        print(f"[DEBUG] Firebase 寫入完成，用時：{time.time() - start:.2f} 秒")

        quick_reply = QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label="A", text="A")),
                QuickReplyItem(action=MessageAction(label="B", text="B")),
                QuickReplyItem(action=MessageAction(label="C", text="C")),
            ]
        )

        line_bot_api.push_message_with_http_info(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=f"📖 {q}\n{opt}", quick_reply=quick_reply)]
            )
        )
        print(f"[DEBUG] LINE 推送完成，用時：{time.time() - start:.2f} 秒")

def clear_quiz_history(user_id):
    db.reference(f"/quiz/{user_id}/history").delete()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

    