from flask import Flask, request, redirect, render_template   # <— acrescente render_template
import os, yt_dlp

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    url = request.args.get("url")
    if not url:                                # primeira vez: mostra a página bonita
        return render_template("index.html")   # <— aqui usa o template

    # ---- restante do código de download (não mexe) ----
    username = os.getenv("IG_USER")
    password = os.getenv("IG_PASS")
    if not username or not password:
        return "Configure IG_USER e IG_PASS no Render", 500

    opts = {
        "username": username,
        "password": password,
        "format": "best[ext=mp4]",
        "quiet": True,
        "no_warnings": True
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return redirect(info["url"])
    except Exception as e:
        return str(e), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
