import os
import shutil
import subprocess
import tempfile

from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

DOWNLOAD_TIMEOUT = 600


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "service": "YT Downloader API"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/download", methods=["POST"])
def download():
    data = request.get_json(silent=True) or {}

    url = data.get("url", "").strip()
    mode = data.get("mode", "video").lower()
    quality = data.get("quality", "720p").lower()

    if not url.startswith(("https://", "http://")):
        return jsonify({"error": "Enter a valid video URL"}), 400

    if mode not in ("video", "audio"):
        return jsonify({"error": "Mode must be video or audio"}), 400

    if quality not in ("1080p", "720p", "480p", "360p"):
        quality = "720p"

    folder = tempfile.mkdtemp(prefix="ytdl_")
    output = os.path.join(folder, "download.%(ext)s")

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--remote-components", "ejs:npm",
        "--js-runtimes", "deno",
        "--socket-timeout", "30",
        "-o", output,
    ]

    if mode == "audio":
        cmd += ["-x", "--audio-format", "mp3"]
    else:
        height = quality[:-1]
        cmd += [
            "-f",
            f"bv*[height<={height}]+ba/b[height<={height}]/b",
            "--merge-output-format", "mp4",
        ]

    cmd += ["--", url]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=DOWNLOAD_TIMEOUT,
        )

        if result.returncode != 0:
            error = (result.stderr or result.stdout or "Download failed")[-1500:]
            shutil.rmtree(folder, ignore_errors=True)
            return jsonify({"error": error}), 502

        files = [
            os.path.join(folder, name)
            for name in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, name))
        ]

        if not files:
            shutil.rmtree(folder, ignore_errors=True)
            return jsonify({"error": "No output file was created"}), 500

        filepath = max(files, key=os.path.getsize)
        filename = "audio.mp3" if mode == "audio" else "video.mp4"

        response = send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
        )
        response.call_on_close(
            lambda: shutil.rmtree(folder, ignore_errors=True)
        )
        return response

    except subprocess.TimeoutExpired:
        shutil.rmtree(folder, ignore_errors=True)
        return jsonify({"error": "Download timed out"}), 504

    except Exception:
        app.logger.exception("Download failed")
        shutil.rmtree(folder, ignore_errors=True)
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
    )
