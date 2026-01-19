from flask import Flask, request, redirect
import os, yt_dlp

app = Flask(__name__)

# ---------- HTML dark GLADIADOR ----------
INDEX_PAGE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>GLADIADOR – InstaDown</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
head>
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
    if not url:                 # primeira vez: só mostra a página
        return INDEX_PAGE

    # ---------- download ----------
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
