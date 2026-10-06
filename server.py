from flask import Flask, request, jsonify, send_file
import os
import subprocess
import tempfile
import shutil

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

    folder = tempfile.mkdtemp(prefix="ytdl_")

    try:
        output = os.path.join(folder, "%(title).100s.%(ext)s")
        cmd = [
    "yt-dlp",
    "--no-playlist",
    "--remote-components", "ejs:npm",
    "--js-runtimes", "deno",
    "-o", output,
]

        if mode == "audio":
            cmd += ["-x", "--audio-format", "mp3"]
        elif quality in ("1080p", "720p", "480p", "360p"):
            height = quality[:-1]
            cmd += [
                "-f",
                f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
            ]
        else:
            cmd += ["-f", "best"]

        cmd += ["--", url]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode != 0:
            error = result.stderr[-1500:]
            shutil.rmtree(folder, ignore_errors=True)
            return jsonify({"error": error}), 500

        files = [
            os.path.join(folder, name)
            for name in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, name))
            and not name.endswith((".part", ".ytdl"))
        ]

        if not files:
            shutil.rmtree(folder, ignore_errors=True)
            return jsonify({"error": "No output file was created"}), 500

        filepath = max(files, key=os.path.getsize)

        response = send_file(
            filepath,
            as_attachment=True,
            download_name=os.path.basename(filepath)
        )
        response.call_on_close(
            lambda: shutil.rmtree(folder, ignore_errors=True)
        )
        return response

    except subprocess.TimeoutExpired:
        shutil.rmtree(folder, ignore_errors=True)
        return jsonify({"error": "Download timed out"}), 504

    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        return jsonify({"error": str(exc)[:500]}), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
