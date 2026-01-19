from flask import Flask, request, redirect, render_template_string
import os, yt_dlp

app = Flask(__name__)

FORM = '''
<form method="get">
  Cole o link do reel: <input name="url" size="60">
  <button type="submit">Baixar</button>
</form>
'''

@app.route("/", methods=["GET"])
def index():
    url = request.args.get("url")
    if not url:                     # primeira vez: mostra o campo
        return FORM

    # --- daqui pra baixo igual ao código anterior ---
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
