from flask import Flask, request, jsonify
import os
import subprocess
import tempfile

app = Flask(__name__)

@app.route("/")
def home():
    return "YT Downloader server is running"

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    mode = data.get("mode", "video")
    quality = data.get("quality", "best")

    if not url.startswith(("https://", "http://")):
        return jsonify({"error": "Enter a valid URL"}), 400

    if mode not in ("video", "audio"):
        return jsonify({"error": "Invalid download mode"}), 400

    with tempfile.TemporaryDirectory() as folder:
        output = os.path.join(folder, "%(title).100s.%(ext)s")
        cmd = ["yt-dlp", "--no-playlist", "-o", output]

        if mode == "audio":
            cmd += ["-x", "--audio-format", "mp3"]
        elif quality in ("1080p", "720p", "480p", "360p"):
            height = quality[:-1]
            cmd += ["-f", f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"]
        else:
            cmd += ["-f", "bestvideo*+bestaudio/best"]

        cmd += ["--", url]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=7200
            )
            if result.returncode != 0:
                return jsonify({"error": result.stderr[-1000:]}), 500

            files = [
                os.path.join(folder, name)
                for name in os.listdir(folder)
                if os.path.isfile(os.path.join(folder, name))
            ]
            if not files:
                return jsonify({"error": "No output file created"}), 500

            return jsonify({
                "status": "completed",
                "message": "Download finished, but file delivery still needs to be connected."
            })
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Download timed out"}), 504

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
