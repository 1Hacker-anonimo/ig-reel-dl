from flask import Flask, request, redirect
import os, yt_dlp

app = Flask(__name__)

INDEX_PAGE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>GLADIADOR – InstaDown</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        /* ---------- RESET ---------- */
        *{margin:0;padding:0;box-sizing:border-box;font-family:Segoe UI,Roboto,Arial,sans-serif}
        body{background:#0a0a0a;color:#e0e0e0;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}
        /* ---------- CARD ---------- */
        .card{background:#111;border:1px solid #222;border-radius:12px;padding:40px 30px;max-width:420px;width:100%;text-align:center;box-shadow:0 0 25px #ff004433}
        h1{color:#ff0044;font-size:2.4rem;margin-bottom:12px;letter-spacing:1px;text-transform:uppercase}
        .sub{color:#aaa;font-size:1rem;margin-bottom:25px}
        /* ---------- FORM ---------- */
        form{display:flex;flex-direction:column;gap:15px}
        input[type=url]{background:#1a1a1a;border:1px solid #333;border-radius:6px;color:#fff;padding:14px 16px;font-size:1rem;transition:border .2}
        input[type=url]:focus{border-color:#ff0044;outline:none}
        .btn{background:#ff0044;color:#fff;border:none;border-radius:6px;padding:14px;font-size:1.05rem;font-weight:bold;cursor:pointer;transition:background .2s}
        .btn:hover{background:#e6003d}
        /* ---------- FOOTER ---------- */
        .foot{margin-top:30px;font-size:.75rem;color:#555}
        /* ---------- LOADER ---------- */
        .overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:#000d;display:none;flex-direction:column;align-items:center;justify-content:center;z-index:999}
        .overlay.show{display:flex}
        .spinner{width:50px;height:50px;border:5px solid #222;border-top-color:#ff0044;border-radius:50%;animation:spin .r 1s linear infinite}
        @keyframes spin{to{transform:rotate(360deg)}}
        . overlay p{margin-top:15px;color:#ff0044;font-weight:bold}
    </style>
</head>
<body>
    <div class="card">
        <h1>GLADIADOR</h1>
        <p class="sub">Cole o link do Instagram e o vídeo baixa automaticamente.</p>

        <form id="form" action="/" method="get">
            <input id="url" name="url" type="url" placeholder="https://www.instagram.com/reel/..." required>
            <button class="btn" type="submit">Baixar</button>
        </form>

        <div class="foot">
            Feito por <strong>GLADIADOR</strong> – 2026
        </div>
    </div>

    <!-- overlay de “baixando...” -->
    <div id="loader" class="overlay">
        <div class="spinner"></div>
        <p>baixando...</p>
    </div>

    <script>
        const form  = document.getElementById('form');
        const input = document.getElementById('url');
        const load  = document.getElementById('loader');

        form.addEventListener('submit', () => load.classList.add('show'));
        input.addEventListener('paste', () => {
            setTimeout(() => {
                load.classList.add('show');
                form.submit();
            }, 100);
        });
    </script>
</body>
</html>
'''

@app.route("/", methods=["GET"])
def index():
    url = request.args.get("url")
    if not url:
        return INDEX_PAGE

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
