import os
import tempfile
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
import subprocess

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route('/transcribe', methods=['POST'])
def transcribe():
    data = request.get_json()
    
    file_url = data.get('file_url', '')
    file_path = data.get('file_path', '')
    
    # To'liq URL tuzish
    if file_path and not file_url:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    
    if not file_url:
        return jsonify({"error": "No file_url or file_path provided"}), 400
    
    try:
        # Faylni yuklab olish
        response = requests.get(file_url, timeout=30)
        response.raise_for_status()
        
        # Temp faylga saqlash
        with tempfile.NamedTemporaryFile(suffix='.oga', delete=False) as tmp_in:
            tmp_in.write(response.content)
            tmp_in_path = tmp_in.name
        
        tmp_out_path = tmp_in_path.replace('.oga', '.mp3')
        
        # ffmpeg bilan MP3 ga o'girish
        subprocess.run([
            'ffmpeg', '-i', tmp_in_path, '-ar', '16000',
            '-ac', '1', '-b:a', '64k', tmp_out_path, '-y'
        ], check=True, capture_output=True)
        
        # Whisper bilan transkript
        with open(tmp_out_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        # Tozalash
        os.unlink(tmp_in_path)
        os.unlink(tmp_out_path)
        
        return jsonify({"text": transcript.text})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
