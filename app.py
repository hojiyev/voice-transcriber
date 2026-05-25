import os
import tempfile
import requests
from flask import Flask, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Gemini mijozini yaratamiz
client = genai.Client(api_key=GEMINI_API_KEY)


def download_telegram_file(file_path):
    """Telegram file_path orqali OGG faylni yuklab olish"""
    download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    response = requests.get(download_url, timeout=60)
    response.raise_for_status()
    return response.content


@app.route("/transcribe", methods=["POST"])
def transcribe():
    data = request.get_json()
    file_path = data.get("file_path", "").strip() if data else ""

    # Agar file_path bo'sh bo'lsa — matn xabari
    if not file_path:
        return jsonify({"text": ""}), 200

    try:
        # 1. Telegram'dan OGG faylni yuklab olish
        file_content = download_telegram_file(file_path)

        # 2. Geminiga inline audio data sifatida yuborish (MP3 konvert kerak emas!)
        prompt = (
            "Quyidagi ovozli xabarni o'zbek tilida aniq va to'liq transkripsiya qil. "
            "Faqat transkripsiya matnini qaytaring, qo'shimcha izoh, tarjima yoki sharh qo'shmang. "
            "Foydalanuvchining ismi Alisher Hodiyev. "
            "Kontekst: Hodiyev Education, Obsidian, Telegram bot, Make.com, Claude, ChatGPT, "
            "Anthropic, Railway, integratsiya, ma'lumotlar bazasi kabi so'zlar uchrashi mumkin. "
            "Agar tushunarsiz qism bo'lsa, [...] bilan belgilang, lekin o'ylab so'z qo'shmang."
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=file_content,
                    mime_type="audio/ogg",
                ),
            ],
            config=types.GenerateContentConfig(
                temperature=0.0,
            ),
        )

        transcript_text = response.text.strip() if response.text else ""
        return jsonify({"text": transcript_text}), 200

    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"Fayl yuklab olishda xato: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Xato: {str(e)}"}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
