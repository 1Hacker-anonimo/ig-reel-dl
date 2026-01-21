app.py
import os, re, json, requests
from flask import Flask, request, Response, render_template_string, redirect, abort

app = Flask(__name__)
sess = requests.Session()
sess.headers.update({
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
    "Accept-Language": "pt-BR,pt=0.9",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
})

def username_from_url(url: str) -> str:
    m = re.search(r"instagram\.com/([^/?]+)", url)
    return m.group(1) if m else url.strip("/@ ")

def ig_public_stories(username: str):
    r = sess.get(f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}")
    if r.status_code == 404: abort(404, "Perfil não existe")
    if r.status_code == 401: abort(401, "login_required – troque de IP ou use cookie fallback")
    data = r.json()
    user = data["data"]["user"]
    if user["is_private"]: abort(403, "Perfil privado – impossível baixar stories")
    user_id = user["id"]
    r = sess.get(
        f"https://i.instagram.com/api/v1/feed/reels_media/?reel_ids={user_id}",
        headers={"X-IG-App-ID": "936619743392459"}
    )
    if r.status_code != 200 or not r.json().get("reels"): return []
    reel = r.json()["reels"][user_id]
    items = []
    for m in reel.get("items", []):
        media_id = m["id"]
        is_video = m["media_type"] == 2
        if is_video:
            url = m["video_versions"][0]["url"]
            thumb = m.get("image_versions2", {}).get("candidates", [{}])[0].get("url", "")
        else:
            url = m["image_versions2"]["candidates"][0]["url"]
            thumb = url
        items.append({"id": media_id, "url": url, "is_video": is_video, "thumbnail": thumb})
    return items

HTML_BASE = """<!doctype html>
<html lang="pt-BR" data-bs-theme="dark">
<head>
  <meta charset="utf-8">
  <title>StorySaver – Download sem login</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body{background:#111;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
    .logo{font-size:1.8rem;font-weight:700;background:linear-gradient(45deg,#833ab4,#fd1d1d,#fcb045);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
    .card-img-top{height:220px;object-fit:cover;}
    .btn-download{background:#fd1d1d;border:none;color:#fff}
    .btn-download:hover{background:#e14a4a}
  </style>
</head>
<body>
<nav class="navbar navbar-dark bg-dark border-bottom">
  <div class="container">
    <span class="logo">StorySaver</span>
  </div>
</nav>
<div class="container py-4">
  <div class="text-center mb-4">
    <h1 class="fw-bold">Baixe stories de perfis públicos</h1>
    <p class="lead">Sem login, sem app, direto no navegador.</p>
  </div>
  <form class="row g-2 justify-content-center" action="/story" method="get">
    <div class="col-12 col-md-6">
      <input type="text" class="form-control form-control-lg" name="url"
             placeholder="@usuario ou URL completa" required>
    </div>
    <div class="col-auto">
      <button class="btn btn-download btn-lg px-4">Buscar</button>
    </div>
  </form>
  {% if stories %}
  <hr>
  <h4 class="mb-3">Stories de <span class="text-primary">@{{ username }}</span></h4>
  <div class="row g-3">
  {% for s in stories %}
    <div class="col-6 col-md-4 col-lg-3">
      <div class="card h-100">
        <img src="{{ s.thumbnail }}" class="card-img-top">
        <div class="card-body d-flex flex-column">
          <span class="badge bg-secondary mb-2">{{ "Vídeo" if s.is_video else "Foto" }}</span>
          <a href="{{ s.url }}" class="btn btn-download mt-auto" download>
            Baixar
          </a>
        </div>
      </div>
    </div>
  {% endfor %}
  </div>
  {% endif %}
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(HTML_BASE, stories=None)

@app.route("/story")
def story_list():
    url_or_user = request.args.get("url") or ""
    if not url_or_user: return redirect("/")
    username = username_from_url(url_or_user)
    try:
        stories = ig_public_stories(username)
    except Exception as e:
        return str(e), 400
    return render_template_string(HTML_BASE, stories=stories, username=username)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
