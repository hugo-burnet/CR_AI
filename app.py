#!/usr/bin/env python3
"""
CR Chantier — Interface Web Locale
Flask + Whisper + Ollama · 100% local
"""

import os
import sys
import json
import tempfile
import datetime
import threading
import subprocess
import webbrowser
import requests as http_req
import numpy as np
from flask import Flask, render_template, request, Response, jsonify, stream_with_context

# ── PyInstaller : résolution des chemins ────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Config ─────────────────────────────────────────────────────────────────────
OLLAMA_URL    = "http://localhost:11434/api/generate"
OLLAMA_TAGS   = "http://localhost:11434/api/tags"
OLLAMA_MODEL  = "gemma4:e4b"
WHISPER_MODEL = "medium"
WHISPER_LANG  = "fr"
SAMPLE_RATE   = 16000
CHANNELS      = 1
OUTPUT_DIR    = os.path.expanduser("~/comptes_rendus")

PROMPT_SYSTEME = """
Tu es un assistant spécialisé en suivi de chantier BTP.
Tu reçois la transcription brute d'une réunion ou d'un échange vocal entre un conducteur de travaux et son équipe.
Ton rôle est de produire un compte-rendu professionnel, structuré et fiable.

RÈGLES ABSOLUES :
- Ne jamais inventer d'informations absentes de la transcription.
- Si une information est floue ou incomplète, indiquer « À clarifier ».
- Utiliser des formulations claires, directes et professionnelles.
- Conserver les noms, dates, références de lots ou d'ouvrages mentionnés.
- Toujours inclure le nom du projet et le contexte fournis dans l'en-tête.

FORMAT DE SORTIE (Markdown) :

# Compte-rendu — [Date]

Projet : [Nom du projet]
Contexte : [Contexte fourni]

## Participants mentionnés
- [liste]

## Contexte / Objet de la réunion
[résumé en 2-3 phrases]

## Points abordés
### 1. [Thème]
- [détail]

## Décisions prises
| Décision | Responsable | Échéance |
|---|---|---|
| ... | ... | ... |

## Actions à mener (To-do)
- [ ] [action] — Responsable : [nom] — Délai : [date ou durée]

## Points en suspens / À clarifier
- [liste]

## Prochaine réunion
[date/lieu si mentionné, sinon « Non définie »]
"""

# ── App ─────────────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB

# ── Global state ────────────────────────────────────────────────────────────────
_lock = threading.Lock()
_state = {
    "recording": False,
    "frames":    [],
    "audio_path": None,
    "sd_stream": None,
}
_whisper_model = None


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _whisper_model


# ── Helpers setup ───────────────────────────────────────────────────────────────

def check_ollama():
    """Retourne (running, model_available, models_list)."""
    try:
        r = http_req.get(OLLAMA_TAGS, timeout=2)
        models = [m["name"] for m in r.json().get("models", [])]
        return True, OLLAMA_MODEL in models, models
    except Exception:
        return False, False, []


def check_whisper_cached():
    cache = os.path.expanduser("~/.cache/huggingface/hub")
    if not os.path.isdir(cache):
        return False
    return any(f"faster-whisper-{WHISPER_MODEL}" in d for d in os.listdir(cache))


# ── Routes : setup ──────────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    ollama_running, model_ok, models = check_ollama()
    whisper_cached = check_whisper_cached()
    return jsonify({
        "ollama_running":  ollama_running,
        "model_available": model_ok,
        "model_name":      OLLAMA_MODEL,
        "whisper_cached":  whisper_cached,
        "whisper_model":   WHISPER_MODEL,
        "models":          models,
    })


@app.route("/api/open-ollama-download")
def open_ollama_download():
    webbrowser.open("https://ollama.com/download/windows")
    return jsonify({"status": "opened"})


@app.route("/api/install-model")
def install_model():
    """SSE : exécute `ollama pull <model>` et stream la progression."""
    def sse(data):
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    def stream():
        try:
            proc = subprocess.Popen(
                ["ollama", "pull", OLLAMA_MODEL],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            yield sse({"error": "ollama introuvable — installez Ollama d'abord."})
            return

        for line in proc.stdout:
            line = line.rstrip()
            if line:
                yield sse({"text": line})

        proc.wait()
        if proc.returncode == 0:
            yield sse({"done": True})
        else:
            yield sse({"error": f"ollama pull a échoué (code {proc.returncode})"})

    return Response(
        stream_with_context(stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/download-whisper")
def download_whisper():
    """SSE : charge le modèle Whisper (déclenche son téléchargement si absent)."""
    def sse(data):
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    def stream():
        yield sse({"text": f"Téléchargement du modèle Whisper '{WHISPER_MODEL}'…"})
        yield sse({"text": "Cela peut prendre plusieurs minutes (~1.5 Go)."})
        try:
            get_whisper_model()
            yield sse({"done": True})
        except Exception as exc:
            yield sse({"error": str(exc)})

    return Response(
        stream_with_context(stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Routes : app principale ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/record/start", methods=["POST"])
def record_start():
    try:
        import sounddevice as sd
    except ImportError:
        return jsonify({"error": "sounddevice non installé"}), 500

    with _lock:
        if _state["recording"]:
            return jsonify({"error": "Enregistrement déjà en cours"}), 400
        _state["frames"] = []
        _state["recording"] = True

    def callback(indata, _fc, _ti, _st):
        with _lock:
            if _state["recording"]:
                _state["frames"].append(indata.copy())

    try:
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                                dtype="float32", callback=callback)
        stream.start()
        with _lock:
            _state["sd_stream"] = stream
    except Exception as exc:
        with _lock:
            _state["recording"] = False
        return jsonify({"error": str(exc)}), 500

    return jsonify({"status": "recording"})


@app.route("/record/stop", methods=["POST"])
def record_stop():
    try:
        import soundfile as sf
    except ImportError:
        return jsonify({"error": "soundfile non installé"}), 500

    with _lock:
        if not _state["recording"]:
            return jsonify({"error": "Aucun enregistrement en cours"}), 400
        _state["recording"] = False
        stream = _state["sd_stream"]
        frames = list(_state["frames"])
        _state["sd_stream"] = None

    if stream:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass

    if not frames:
        return jsonify({"error": "Aucun audio capturé"}), 400

    audio = np.concatenate(frames, axis=0)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio, SAMPLE_RATE)

    with _lock:
        _state["audio_path"] = tmp.name

    return jsonify({"status": "stopped", "duration": round(len(audio) / SAMPLE_RATE, 1)})


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier reçu"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Nom de fichier vide"}), 400

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in {".wav", ".mp3", ".m4a", ".ogg", ".flac"}:
        return jsonify({"error": f"Format non supporté : {ext}"}), 400

    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    f.save(tmp.name)
    with _lock:
        _state["audio_path"] = tmp.name

    return jsonify({"status": "uploaded", "filename": f.filename})


@app.route("/open-file")
def open_file():
    path = request.args.get("path", "")
    if os.path.isfile(path):
        os.startfile(path)
        return jsonify({"status": "opened"})
    return jsonify({"error": "Fichier introuvable"}), 404


@app.route("/generate")
def generate():
    nom_projet = request.args.get("nom_projet", "").strip()
    contexte   = request.args.get("contexte", "").strip()

    with _lock:
        audio_path = _state.get("audio_path")

    if not audio_path or not os.path.isfile(audio_path):
        return jsonify({"error": "Aucun fichier audio disponible"}), 400

    def sse(data):
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    def stream():
        yield sse({"type": "status", "step": 1, "message": "Chargement de Whisper…"})
        try:
            model = get_whisper_model()
        except Exception as exc:
            yield sse({"type": "error", "message": f"Whisper : {exc}"}); return

        yield sse({"type": "status", "step": 1, "message": "Transcription en cours…"})
        try:
            segments, _ = model.transcribe(audio_path, language=WHISPER_LANG,
                                           beam_size=5, vad_filter=True)
            transcription = " ".join(s.text.strip() for s in segments)
        except Exception as exc:
            yield sse({"type": "error", "message": f"Transcription : {exc}"}); return

        yield sse({"type": "transcription", "text": transcription, "chars": len(transcription)})
        yield sse({"type": "status", "step": 2, "message": f"Transcription OK — {len(transcription)} caractères"})
        yield sse({"type": "status", "step": 3, "message": f"Rédaction avec {OLLAMA_MODEL}…"})

        date_str = datetime.datetime.now().strftime("%d/%m/%Y à %H:%M")
        prompt = (
            f"Date : {date_str}\n"
            f"Projet : {nom_projet or 'Non précisé'}\n"
            f"Contexte : {contexte or 'Non précisé'}\n\n"
            f"TRANSCRIPTION BRUTE :\n{transcription}\n\n"
            f"Génère le compte-rendu selon le format demandé."
        )
        payload = {"model": OLLAMA_MODEL, "prompt": prompt,
                   "system": PROMPT_SYSTEME, "stream": True}

        try:
            resp = http_req.post(OLLAMA_URL, json=payload, stream=True, timeout=300)
            resp.raise_for_status()
        except http_req.exceptions.ConnectionError:
            yield sse({"type": "error", "message": "Ollama hors ligne — lancez : ollama serve"}); return
        except Exception as exc:
            yield sse({"type": "error", "message": f"Ollama : {exc}"}); return

        cr_parts = []
        for line in resp.iter_lines():
            if not line: continue
            try:
                data = json.loads(line)
                token = data.get("response", "")
                if token:
                    cr_parts.append(token)
                    yield sse({"type": "token", "text": token})
                if data.get("done"): break
            except json.JSONDecodeError:
                continue

        cr_text = "".join(cr_parts)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        stamp    = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        filepath = os.path.join(OUTPUT_DIR, f"CR_{stamp}.md")

        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(cr_text)
            fh.write("\n\n---\n\n## Transcription brute\n\n")
            fh.write(transcription)

        yield sse({"type": "done", "file": filepath})

    return Response(stream_with_context(stream()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Lancement ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    def _open():
        import time; time.sleep(1.2)
        webbrowser.open("http://localhost:5000")

    threading.Thread(target=_open, daemon=True).start()
    print("CR Chantier — http://localhost:5000")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
