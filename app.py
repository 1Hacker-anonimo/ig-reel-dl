from flask import Flask, request, Response, redirect, stream_with_context
import os, requests, logging, re
from requests.exceptions import RequestException
from urllib.parse import quote

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

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

    <div class="menu-icon" onclick="togglePanel()">
        <span></span><span></span><span></span>
    </div>

    <div id="sidePanel" class="side-panel">
        <h2>TikTok Sem Marca d'Água</h2>
        <form action="/story" method="get">
            <input name="url" type="url" placeholder="https://www.tiktok.com/..." required>
            <button class="btn" type="submit">Baixar TikTok</button>
        </form>

        <h2>YouTube</h2>
        <form id="ytForm">
            <input id="ytUrl" type="url" placeholder="https://youtu.be/..." required>
            <button class="btn" type="button" onclick="downloadYt('mp4')">Vídeo MP4</button>
            <button class="btn" type="button" onclick="downloadYt('mp3')">Áudio MP3</button>
        </form>
    </div>

    <div class="card">
        <h1>GLADIADOR</h1>
        <p class="sub">Cole o link do Instagram e o vídeo baixa automaticamente.</p>

        <form id="form" action="/dl" method="get">
            <input name="url" type="url" placeholder="https://www.instagram.com/reel/..." required>
            <button class="btn" type="submit">Baixar</button>
        </form>

        <div class="foot">Feito por <strong>GLADIADOR</strong> – 2026</div>
    </div>

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

        document.getElementById('form').addEventListener('submit', showLoader);

        function downloadYt(fmt){
            const url = document.getElementById('ytUrl').value.trim();
            if(!url) return alert('Cole um link do YouTube.');
            showLoader();
            window.location.href = `/yt?url=${encodeURIComponent(url)}&fmt=${fmt}`;
        }
    </script>
</body>
</html>
'''

# ---------- TIKTOK ----------
def extract_video_id(url: str) -> str:
    """
    Extrai o ID do vídeo TikTok de qualquer formato de URL (2026 compatível)
    """
    # Remove query strings e fragments
    clean_url = re.sub(r'\?.*$', '', url).rstrip('/')

    # Padrões comuns em 2026
    patterns = [
        r'/video/(\d{18,})',                  # Padrão principal: /@user/video/123...
        r'/v/(\d{18,})',                      # Mobile: /v/123...
        r'vt\.tiktok\.com/[^/]+/(\d+)',       # Short vt.tiktok.com/...
        r't\.tiktok\.com/[^/]+/(\d+)',        # Outro short
        r'm\.tiktok\.com/v/(\d+)',            # m.tiktok.com/v/...
        r'(\d{18,})',                         # Último recurso: ID solto longo
    ]

    for pattern in patterns:
        match = re.search(pattern, clean_url)
        if match:
            video_id = match.group(1)
            logging.info(f"ID encontrado com padrão '{pattern}': {video_id}")
            return video_id

    raise ValueError("ID do vídeo não encontrado na URL. Certifique-se de que é um link válido de vídeo TikTok (ex: https://www.tiktok.com/@user/video/7501234567890123456)")

def get_tiktok_no_watermark_url(tiktok_url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/"
    }

    # Tentativa 1: SnapTik API (se ainda funcionar)
    try:
        api = "https://api.snaptik.app/v1/info"
        payload = {"url": tiktok_url}
        r = requests.post(api, json=payload, headers=headers, timeout=12)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "ok":
            nw_url = data["video"].get("noWatermark") or data["video"].get("no_watermark")
            if nw_url:
                logging.info("SnapTik API funcionou!")
                return nw_url
    except Exception as e:
        logging.warning(f"SnapTik API falhou: {e}")

    # Fallback: SSSTik (parse HTML - mais estável em 2026)
    try:
        ssstik_endpoint = f"https://ssstik.io/abc?url={quote(tiktok_url)}"
        resp = requests.get(ssstik_endpoint, headers=headers, timeout=15)
        resp.raise_for_status()

        # Procura link sem watermark (padrão comum no HTML)
        match = re.search(r'href="(https?://[^"]*without[_-]?watermark[^"]*)"', resp.text, re.IGNORECASE)
        if match:
            nw_url = match.group(1)
            logging.info("SSSTik fallback funcionou!")
            return nw_url

        # Alternativa: procura por 'without wm' ou classes comuns
        match_alt = re.search(r'(https?://[^"\']+\.mp4[^"\']*without[^"\']*)', resp.text, re.IGNORECASE)
        if match_alt:
            nw_url = match_alt.group(1)
            logging.info("SSSTik alt match funcionou!")
            return nw_url

    except Exception as e:
        logging.warning(f"SSSTik fallback falhou: {e}")

    raise ValueError("Não foi possível obter link sem watermark (SnapTik e SSSTik falharam). Tente outra URL ou verifique se o vídeo é público.")

# ---------- ROTAS ----------
@app.route("/")
def home():
    return INDEX_PAGE

@app.route("/dl")          # Instagram
def download():
    url = request.args.get("url")
    if not url:
        return redirect("/")

    username = os.getenv("IG_USER")
    password = os.getenv("IG_PASS")
    if not username or not password:
        return "Configure IG_USER e IG_PASS no Render", 500

    import yt_dlp
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
    except Exception as e:
        logging.exception("IG erro")
        return f"Erro ao obter vídeo Instagram: {str(e)}", 400

    def generate():
        try:
            with requests.get(video_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=16*1024):
                    if chunk:
                        yield chunk
        except RequestException:
            logging.exception("stream IG")
    return Response(
        stream_with_context(generate()),
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "video/mp4",
        }
    )

@app.route("/story")       # TikTok Sem Marca
def tiktok_dl():
    url = request.args.get("url")
    if not url:
        return redirect("/")

    try:
        logging.info(f"Processando TikTok URL: {url}")
        video_id = extract_video_id(url)
        logging.info(f"ID extraído: {video_id}")

        # Pega URL sem watermark
        video_url = get_tiktok_no_watermark_url(url)

        filename = f"tiktok_{video_id}.mp4"
        r = requests.get(video_url, stream=True, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        r.raise_for_status()

        return Response(
            stream_with_context(r.iter_content(chunk_size=16*1024)),
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "video/mp4",
            }
        )

    except Exception as e:
        logging.exception("TikTok erro completo")
        return f"Erro ao obter vídeo TikTok: {str(e)}<br><br>Dica: Use um link completo como https://www.tiktok.com/@usuario/video/7501234567890123456", 400

@app.route("/yt")          # YouTube
def youtube():
    url = request.args.get("url")
    fmt = request.args.get("fmt")
    if not url or fmt not in ("mp4", "mp3"):
        return redirect("/")

    import yt_dlp
    ydl_opts = {
        "outtmpl": "static/%(title)s.%(ext)s",
        "cookiefile": "cookies.txt",
        "user_agent": "Mozilla/5.0",
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
    except Exception as e:
        logging.exception("YT erro")
        return f"Erro ao obter mídia YouTube: {str(e)}", 400

    def generate():
        try:
            with requests.get(media_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=16*1024):
                    if chunk:
                        yield chunk
        except RequestException:
            logging.exception("stream YT")
    return Response(
        stream_with_context(generate()),
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "audio/mpeg" if fmt == "mp3" else "video/mp4",
        }
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
