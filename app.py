from flask import Flask, request, Response, redirect, stream_with_context
import os, yt_dlp, requests, logging, re
from requests.exceptions import RequestException
import yt_dlp.utils

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# ---------- HTML ----------
INDEX_PAGE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>GLADIADOR – Downloader</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        *{margin:0;padding:0;box-sizing:border-box;font-family:Segoe UI,Roboto,Arial,sans-serif}
        body{background:#0a0a0a;color:#e0e0e0;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}
        .card{background:#111;border:1px solid #222;border-radius:12px;padding:40px 30px;max-width:420px;width:100%;text-align:center;box-shadow:0 0 25px #ff004433}
        h1{color:#ff0044;font-size:2.4rem;margin-bottom:12px;letter-spacing:1px;text-transform:uppercase}
        .sub{color:#aaa;font-size:1rem;margin-bottom:25px}
        form{display:flex;flex-direction:column;gap:15px}
        input[type=url]{background:#1a1a1a;border:1px solid #333;border-radius:6px;color:#fff;padding:14px 16px;font-size:1rem;transition:border .2s}
        input[type=url]:focus{border-color:#ff0044;outline:none}
        .btn{background:#ff0044;color:#fff;border:none;border-radius:6px;padding:14px;font-size:1.05rem;font-weight:bold;cursor:pointer;transition:background .2s}
        .btn:hover{background:#e6003d}
        .foot{margin-top:30px;font-size:.75rem;color:#555}
        .overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:#000d;display:none;flex-direction:column;align-items:center;justify-content:center;z-index:999}
        .overlay.show{display:flex}
        .spinner{width:50px;height:50px;border:5px solid #222;border-top-color:#ff0044;border-radius:50%;animation:spin 1s linear infinite}
        @keyframes spin{to{transform:rotate(360deg)}}
        .overlay p{margin-top:15px;color:#ff0044;font-weight:bold}

        /* -- menu hamburger -- */
        .menu-icon{position:fixed;top:20px;left:20px;cursor:pointer;z-index:1001}
        .menu-icon span{display:block;width:28px;height:3px;background:#ff0044;margin:6px 0;transition:.3s}
        .side-panel{position:fixed;top:0;left:-50%;width:50%;height:100%;background:#111;border-right:1px solid #222;padding:30px;overflow-y:auto;transition:left .3s;z-index:1000}
        .side-panel.show{left:0}
        .side-panel h2{color:#ff0044;margin-bottom:15px}
        .side-panel p, .side-panel li{color:#ccc;font-size:.9rem;line-height:1.4;margin-bottom:10px}
        .side-panel ul{margin-left:20px}
        .side-panel input{width:100%;margin-bottom:10px}
        .side-panel .btn{width:100%;margin-bottom:20px}
    </style>
</head>
<body>

    <!-- ícone hambúrguer -->
    <div class="menu-icon" onclick="togglePanel()">
        <span></span><span></span><span></span>
    </div>

    <!-- painel lateral -->
    <div id="sidePanel" class="side-panel">
        <h2>Instagram Stories</h2>
        <p>O perfil DEVE ser público. Copie o link da foto/vídeo dentro do story.</p>
        <ol>
            <li>Abra o perfil público no navegador.</li>
            <li>Clique na story desejada.</li>
            <li>Copie o URL (deve conter /stories/).</li>
            <li>Coloque abaixo e clique em “Baixar Story”.</li>
        </ol>
        <form action="/story" method="get">
            <input name="url" type="url" placeholder="https://www.instagram.com/stories/..." required>
>
            <button class="btn" type="submit">Baixar Story</button>
        </form>

        <h2>YouTube</h2>
        <p>Cole o link do vídeo e escolha o formato.</p>
        <form id="ytForm">
            <input id="ytUrl" type="url" placeholder="https://youtu.be/..." required>
            <button class="btn" type="button" onclick="downloadYt('mp4')">Vídeo MP4</button>
            <button class="btn" type="button" onclick="downloadYt('mp3')">Áudio MP3</button>
        </form>
    </div>

    <!-- conteúdo principal -->
    <div class="card">
        <h1>GLADIADOR</h1>
        <p class="sub">Cole o link do Instagram e o vídeo baixa automaticamente.</p>

        <form id="form" action="/dl" method="get">
            <input name="url" type="url" placeholder="https://www.instagram.com/reel/..." required>
            <button class="btn" type="submit">Baixar</button>
        </form>

        <div class="foot">Feito por <strong>GLADIADOR</strong> – 2026</div>
    </div>

    <!-- loader -->
    <div id="loader" class="overlay">
        <div class="spinner"></div>
        <p>baixando...</p>
    </div>

    <script>
        function togglePanel(){
            document.getElementById('sidePanel').classList.toggle('show');
        }

        function showLoader(){
            const l = document.getElementById('loader');
            l.classList.add('show');
            setTimeout(() => l.classList.remove('show'), 1000);
        }

        // forms normais
        document.getElementById('form').addEventListener('submit', showLoader);

        // youtube
        function downloadYt(fmt){
            const url = document.getElementById('ytUrl').value.trim();
            if(!url) return alert('Cole um link do YouTube.');
            showLoader();
            // abre a rota /yt com parâmetros
            window.location.href = `/yt?url=${encodeURIComponent(url)}&fmt=${fmt}`;
        }
    </script>
</body>
</html>
'''

# ---------- FUNÇÕES AUXILIARES ----------
def username_from_url(url: str) -> str:
    m = re.search(r"instagram\.com/([^/?]+)", url)
    return m.group(1) if m else url.strip("/@ ")

def ig_stories_data(url_or_user: str):
    """
    Cookies salvo em cookies.txt (Netscape) evita 'login_required'.
    Retorna lista [{url, thumbnail, is_video}] ou dict {error}.
    """
    username = username_from_url(url_or_user)
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "cookiefile": "cookies.txt",          # <── usa seus cookies
        "format": "best",
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # extrai ID do perfil
            info = ydl.extract_info(f"https://www.instagram.com/{username}/", download=False)
            user_id = info["id"]

        # agora pega os stories com os mesmos cookies
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
            "Accept-Language": "pt-BR,pt=0.9",
            "X-IG-App-ID": "936619743392459",
            "Cookie": open("cookies.txt").read().replace("\n", "; "),  # envia cookies inline
        }
        r = requests.get(
            f"https://i.instagram.com/api/v1/feed/reels_media/?reel_ids={user_id}",
            headers=headers,
            timeout=15,
        )
        if r.status_code != 200 or not r.json().get("reels"):
            return []
        reel = r.json()["reels"][user_id]
        items = []
        for m in reel.get("items", []):
            media_id = m["id"]
            is_video = m["media_type"] == 2
            if is_video:
                url = m["video_versions"][0]["url"]
                thumb = m.get("image_versions2",  {}).get("candidates", [{}])[0].get("url", "")
            else:
                url = m["image_versions2"]["candidates"][0]["url"]
                thumb = url
            items.append({"id": media_id, "url": url, "is_video": is_video, "thumbnail": thumb})
        return items
    except Exception as e:
        logging.exception("Erro stories com cookies")
        return {"error": str(e)}


# ---------- ROTAS ----------
@app.route("/")
def home():
    return INDEX_PAGE

@app.route("/dl")          # Instagram (feed, reel, stories)
def download():
    url = request.args.get("url")
    if not url:
        return redirect("/")

    username = os.getenv("IG_USER")
    password = os.getenv("IG_PASS")
    if not username or not password:
        return "Configure IG_USER e IG_PASS no Render", 500

    ydl_opts = {
        "username": username,
        "password": password,
        "format": "best[ext=mp4]",
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info["url"]
            filename = f"{info['id']}.mp4"
    except yt_dlp.utils.DownloadError as e:
        logging.exception("yt-dlp falhou")
        return f"Erro ao obter vídeo: {e}", 400
    except Exception as e:
        logging.exception("Exceção geral ao extrair")
        return f"Erro desconhecido: {e}", 500

    def generate():
        try:
            with requests.get(video_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=16*1024):
                    if chunk:
                        yield chunk
        except RequestException:
            logging.exception("Erro no stream")
            return
        except Exception:
            logging.exception("Exceção geral no stream")
            return

    return Response(
        stream_with_context(generate()),
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "video/mp4",
        }
    )

@app.route("/story")       # NOVA ROTA Stories
def story_dl():
    url_or_user = request.args.get("url")
    if not url_or_user:
        return redirect("/")
    data = ig_stories_data(url_or_user)
    if isinstance(data, dict) and data.get("error"):
        return data["error"], 400
    if not data:
        return "Nenhum story encontrado.", 404

    # monta página simples com os stories
    cards = "\n".join(
        f"""
        <div class="card mb-3" style="max-width:400px;margin:auto">
            <img src="{s['thumbnail']}" class="card-img-top">
            <div class="card-body text-center">
                <span class="badge bg-secondary">{"Vídeo" if s['is_video'] else "Foto"}</span>
                <a href="{s['url']}" class="btn btn-download mt-2" download>Baixar</a>
            </div>
        </div>
        """
        for s in data
    )
    html = f"""
    <!doctype html>
    <html lang="pt-BR" data-bs-theme="dark">
    <head>
      <meta charset="utf-8">
      <title>Stories – GLADIADOR</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
      <style>
        body{{background:#111;color:#e0e0e0}}
        .btn-download{{background:#ff0044;border:none;color:#fff}}
        .btn-download:hover{{background:#e6003d}}
      </style>
    </head>
    <body>
      <div class="container py-4">
        <h4 class="text-center mb-4">Stories</h4>
        {cards}
        <div class="text-center mt-4">
          <a href="/" class="btn btn-download">Voltar</a>
        </div>
      </div>
    </body>
    </html>
    """
    return html

@app.route("/yt")          # YouTube (vídeo ou mp3)
def youtube():
    url = request.args.get("url")
    fmt = request.args.get("fmt")          # mp4 ou mp3
    if not url or fmt not in ("mp4", "mp3"):
        return redirect("/")

    ydl_opts = {
        "format": "bestaudio/best" if fmt == "mp3" else "best[ext=mp4]",
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "outtmpl": "%(id)s.%(ext)s",
    }
    if fmt == "mp3":
        ydl_opts.update({
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            media_url = info["url"]
            filename = f"{info['id']}.{fmt}"
    except yt_dlp.utils.DownloadError as e:
        logging.exception("yt-dlp YouTube falhou")
        return f"Erro ao obter mídia: {e}", 400
    except Exception as e:
        logging.exception("Exceção geral YouTube")
        return f"Erro desconhecido: {e}", 500

    def generate():
        try:
            with requests.get(media_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=16*1024):
                    if chunk:
                        yield chunk
        except RequestException:
            logging.exception("Erro no stream YouTube")
            return
        except Exception:
            logging.exception("Exceção geral stream YouTube")
            return

    return Response(
        stream_with_context(generate()),
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "audio/mpeg" if fmt == "mp3" else "video/mp4",
        }
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
