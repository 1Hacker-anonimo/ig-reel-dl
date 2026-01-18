from flask import Flask, request, send_file, render_template_string
import yt_dlp, os, uuid

app = Flask(__name__)

HTML = '''
<!doctype html>
<title>Reel Downloader</title>
<meta name="viewport" content="width=device-width">
<style>
body{font-family:Arial;background:#111;color:#eee;display:flex;justify-content:center;align-items:center;height:100vh}
.box{background:#222;padding:25px;border-radius:8px;text-align:center;width:90%;max-width:400px}
input{width:100%;padding:10px;margin:10px 0}
button{width:100%;padding:12px;background:#e91e63;border:0;color:#fff;font-size:16px}
</style>
<div class="box">
  <h2> Cole o link do Reel </h2>
  <form action="/download" method="post">
    <input name="url" placeholder="https://www.instagram.com/reel/ABC123DEF/" required>
    <button type="submit">Baixar MP4</button>
  </form>
</div>
'''

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/download", methods=["POST"])
def download():
    url = request.form["url"].strip()
    out = f"/sdcard/Download/{uuid.uuid4().hex}.mp4"   # salva visível na galeria
    ydl_opts = {"outtmpl": out, "format": "best"}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return send_file(out, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
