import os
import tempfile
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
import subprocess

app = Flask(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

client = OpenAI(api_key=OPENAI_API_KEY)

def download_telegram_file(file_path):
    """Telegram file_path orqali faylni yuklab olish"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_path}"
    # Avval file_id dan haqiqiy path olish kerak bo'lsa
    # Lekin Make.com dan file_path to'g'ridan-to'g'ri keladi
    download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    response = requests.get(download_url)
    response.raise_for_status()
    return response.content

@app.route("/transcribe", methods=["POST"])
def transcribe():
    data = request.get_json()

    file_path = data.get("file_path", "").strip() if data else ""

    # Agar file_path bo'sh bo'lsa — matn xabari, bo'sh text qaytaramiz
    if not file_path:
        return jsonify({"text": ""}), 200

    try:
        # Telegram'dan faylni yuklab olish
        file_content = download_telegram_file(file_path)

        # Vaqtinchalik .oga fayl saqlaymiz
        with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as tmp_oga:
            tmp_oga.write(file_content)
            tmp_oga_path = tmp_oga.name

        # ffmpeg bilan .oga → .mp3 ga o'tkazamiz
        tmp_mp3_path = tmp_oga_path.replace(".oga", ".mp3")
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_oga_path, "-ar", "16000", "-ac", "1", "-b:a", "64k", tmp_mp3_path],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            os.unlink(tmp_oga_path)
            return jsonify({"error": f"ffmpeg xatosi: {result.stderr}"}), 500

       with open(tmp_mp3_path, "rb") as audio_file:
    transcript = client.audio.transcriptions.create(
        model="gpt-4o-transcribe",
        file=audio_file,
        language="uz",
        prompt="Foydalanuvchi o'zbek tilida gaplashadi. Ismi Alisher. Hodiyev Education o'quv markazi, Obsidian, ChatGPT, Claude, Make.com, Telegram bot, Python kabi atamalar uchrashi mumkin. Lotin yozuvida yoz.",
        response_format="json"
    )

        # Vaqtinchalik fayllarni o'chirish
        os.unlink(tmp_oga_path)
        os.unlink(tmp_mp3_path)

        return jsonify({"text": transcript.text}), 200

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
