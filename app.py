from flask import Flask, request, jsonify
import openai, subprocess, os, tempfile, requests

app = Flask(__name__)
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/transcribe", methods=["POST"])
def transcribe():
    try:
        data = request.get_json()
        if not data or "file_url" not in data:
            return jsonify({"error": "file_url majburiy"}), 400
        file_url = data["file_url"]
        response = requests.get(file_url, timeout=30)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as f:
            f.write(response.content)
            oga_path = f.name
        mp3_path = oga_path.replace(".oga", ".mp3")
        subprocess.run(["ffmpeg", "-y", "-i", oga_path, "-ar", "16000", "-ac", "1", "-b:a", "32k", mp3_path], check=True, capture_output=True)
        with open(mp3_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file, language="uz")
        os.unlink(oga_path)
        os.unlink(mp3_path)
        return jsonify({"text": transcript.text})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"ffmpeg: {e.stderr.decode()}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
