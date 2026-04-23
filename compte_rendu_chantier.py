#!/usr/bin/env python3
"""
Compte-rendu de réunion de chantier — 100% local
Pipeline : Micro → Whisper (faster-whisper) → Ollama (Gemma)

Installation (une seule fois) :
    pip install faster-whisper sounddevice soundfile numpy requests

Ollama doit tourner avec Gemma :
    ollama run gemma3:4b
"""

import os
import sys
import json
import time
import wave
import tempfile
import datetime
import threading
import requests
import numpy as np

# ── Configuration ──────────────────────────────────────────────────────────────
OLLAMA_URL    = "http://localhost:11434/api/generate"
OLLAMA_MODEL  = "gemma4:e4b"          # changer si tu utilises un autre tag
WHISPER_MODEL = "medium"             # tiny | base | small | medium | large-v3
WHISPER_LANG  = "fr"
SAMPLE_RATE   = 16000
CHANNELS      = 1
OUTPUT_DIR    = os.path.expanduser("~/comptes_rendus")  # dossier de sauvegarde
# ───────────────────────────────────────────────────────────────────────────────

PROMPT_SYSTEME = """
Tu es un assistant spécialisé en suivi de chantier BTP. 
Tu reçois la transcription brute d'une réunion ou d'un échange vocal entre un conducteur de travaux et son équipe.
Ton rôle est de produire un compte-rendu professionnel, structuré et fiable.

RÈGLES ABSOLUES :
- Ne jamais inventer d'informations absentes de la transcription.
- Si une information est floue ou incomplète, indiquer « À clarifier ».
- Utiliser des formulations claires, directes et professionnelles.
- Conserver les noms, dates, références de lots ou d'ouvrages mentionnés.

FORMAT DE SORTIE (Markdown) :

# Compte-rendu — [Date]

## Participants mentionnés
- [liste]

## Contexte / Objet de la réunion
[résumé en 2-3 phrases]

## Points abordés
### 1. [Thème]
- [détail]

### 2. [Thème]
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

# ── Couleurs terminal ───────────────────────────────────────────────────────────
def c(text, code): return f"\033[{code}m{text}\033[0m"
BOLD  = lambda t: c(t, "1")
GREEN = lambda t: c(t, "32")
CYAN  = lambda t: c(t, "36")
YELLOW= lambda t: c(t, "33")
RED   = lambda t: c(t, "31")
DIM   = lambda t: c(t, "2")

def titre():
    print("\n" + "═"*58)
    print(BOLD(CYAN("  🏗️  Compte-rendu de chantier  —  IA locale")))
    print(DIM("  Whisper + Ollama/Gemma  •  100% hors-ligne"))
    print("═"*58 + "\n")

# ── Enregistrement audio ────────────────────────────────────────────────────────
def enregistrer() -> str:
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError:
        print(RED("✗  Modules manquants. Lance :  pip install sounddevice soundfile"))
        sys.exit(1)

    print(YELLOW("🎙  Appuie sur  ENTRÉE  pour démarrer l'enregistrement…"))
    input()

    frames = []
    stop_event = threading.Event()

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                            dtype="float32", callback=callback)

    print(GREEN("● Enregistrement en cours…  (ENTRÉE pour arrêter)"))
    with stream:
        input()
        stop_event.set()

    print(DIM("  Arrêt de l'enregistrement."))

    audio = np.concatenate(frames, axis=0)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio, SAMPLE_RATE)
    print(DIM(f"  Fichier temporaire : {tmp.name}"))
    return tmp.name


# ── Transcription Whisper ───────────────────────────────────────────────────────
def transcrire(audio_path: str) -> str:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print(RED("✗  faster-whisper manquant. Lance :  pip install faster-whisper"))
        sys.exit(1)

    print(f"\n{CYAN('◎')} Chargement du modèle Whisper ({WHISPER_MODEL})…")
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")

    print(f"{CYAN('◎')} Transcription en cours…")
    segments, info = model.transcribe(audio_path, language=WHISPER_LANG,
                                      beam_size=5, vad_filter=True)

    texte = " ".join(seg.text.strip() for seg in segments)
    print(GREEN(f"✓  Transcription terminée  ({len(texte)} caractères)"))
    return texte


# ── Génération du compte-rendu via Ollama ──────────────────────────────────────
def generer_cr(transcription: str) -> str:
    date_str = datetime.datetime.now().strftime("%d/%m/%Y à %H:%M")
    prompt = (f"Date de l'enregistrement : {date_str}\n\n"
              f"TRANSCRIPTION BRUTE :\n{transcription}\n\n"
              f"Génère le compte-rendu selon le format demandé.")

    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "system": PROMPT_SYSTEME,
        "stream": True,
    }

    print(f"\n{CYAN('◎')} Rédaction du compte-rendu avec {OLLAMA_MODEL}…\n")
    print("─"*58)

    try:
        resp = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=300)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(RED("✗  Impossible de joindre Ollama. Vérifie qu'il tourne : ollama serve"))
        sys.exit(1)

    compte_rendu = []
    for line in resp.iter_lines():
        if not line:
            continue
        try:
            data = json.loads(line)
            token = data.get("response", "")
            print(token, end="", flush=True)
            compte_rendu.append(token)
            if data.get("done"):
                break
        except json.JSONDecodeError:
            continue

    print("\n" + "─"*58)
    return "".join(compte_rendu)


# ── Sauvegarde ─────────────────────────────────────────────────────────────────
def sauvegarder(cr: str, transcription: str):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    fichier = os.path.join(OUTPUT_DIR, f"CR_{stamp}.md")

    contenu = cr + "\n\n---\n\n## Transcription brute\n\n> " + transcription

    with open(fichier, "w", encoding="utf-8") as f:
        f.write(contenu)

    print(f"\n{GREEN('✓')}  Compte-rendu sauvegardé : {BOLD(fichier)}")
    return fichier


# ── Menu principal ─────────────────────────────────────────────────────────────
def menu_source() -> str:
    print("Source audio :\n")
    print(f"  {BOLD('1')}  Enregistrer maintenant (microphone)")
    print(f"  {BOLD('2')}  Utiliser un fichier audio existant")
    print()
    choix = input("Ton choix (1/2) : ").strip()
    if choix == "2":
        path = input("Chemin du fichier audio : ").strip().strip('"')
        if not os.path.isfile(path):
            print(RED("✗  Fichier introuvable."))
            sys.exit(1)
        return path
    return None  # => enregistrement micro


def main():
    titre()

    # Source audio
    audio_path = menu_source()
    if audio_path is None:
        audio_path = enregistrer()

    # Transcription
    texte = transcrire(audio_path)

    # Affichage de la transcription brute
    print(f"\n{DIM('── Transcription brute ──')}")
    print(DIM(texte[:600] + ("…" if len(texte) > 600 else "")))

    # Compte-rendu
    cr = generer_cr(texte)

    # Sauvegarde
    sauvegarder(cr, texte)

    print(f"\n{GREEN('✓')}  Terminé.\n")


if __name__ == "__main__":
    main()
