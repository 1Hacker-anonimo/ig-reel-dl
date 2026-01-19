from flask import Flask, request, Response, redirect, stream_with_context
import os, yt_dlp, requests, logging
from requests.exceptions import RequestException
import yt_dlp.utils

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

INDEX_PAGE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>GLADIADOR – InstaDown</title>
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
    </style>
</head>
<body>
    <div class="card">
        <h1>GLADIADOR</h1>
        <p class="sub">Cole o link do Instagram e o vídeo baixa automaticamente.</p>

        <form id="form" action="/dl" method="get">
            <input id="url" name="url" type="url" placeholder="https://www.instagram.com/reel/..." required>
            <button class="btn" type="submit">Baixar</button>
        </form>

        <div class="foot">Feito por <strong>GLADIADOR</strong> – 2026</div>
    </div>

    <div id="loader" class="overlay">
        <div class="spinner"></div>
        <p>baixando...</p>
    </div>

    <script>
        const form  = document.getElementById('form');
        const load  = document.getElementById('loader');
        form.addEventListener('submit', () => load.classList.add('show'));
    </script>
</body>
</html>
'''

@app.route("/")
def home():
    return INDEX_PAGE

@app.route("/dl")
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
        except RequestException as e:
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
