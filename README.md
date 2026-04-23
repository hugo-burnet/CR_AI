# CR Chantier — Compte-Rendu IA

> Génération automatique de comptes-rendus de réunions de chantier BTP, 100 % locale.  
> Pipeline : **enregistrement micro → transcription Whisper → rédaction Gemma via Ollama**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask)
![Ollama](https://img.shields.io/badge/Ollama-local-FF6B35)
![Whisper](https://img.shields.io/badge/Whisper-medium-00A67E)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Aperçu

CR Chantier est une application web locale qui remplace la prise de notes en réunion de chantier. Elle enregistre la réunion (ou importe un fichier audio), transcrit automatiquement la parole, puis rédige un compte-rendu structuré en Markdown — le tout **sans connexion internet, sans cloud, sans abonnement**.

### Fonctionnalités

- **Enregistrement microphone** en un clic avec timer en temps réel
- **Import de fichiers audio** (.wav, .mp3, .m4a, .ogg, .flac)
- **Transcription vocale** via Whisper (faster-whisper, modèle medium)
- **Rédaction par LLM** via Ollama (Gemma 4) avec streaming token par token
- **Compte-rendu structuré** : participants, points abordés, décisions, actions, points en suspens
- **Sauvegarde automatique** en `.md` dans `~/comptes_rendus/`
- **Assistant d'installation intégré** : détecte les composants IA manquants et guide l'installation
- **Exportable en `.exe`** Windows via PyInstaller — zéro installation Python requise

---

## Capture d'écran

```
┌─────────────────────────────────────────┐
│  CR Chantier          Ollama actif  ●  │
├─────────────────────────────────────────┤
│  1. Informations du projet              │
│     Nom du projet  [_______________]    │
│     Contexte       [_______________]    │
├─────────────────────────────────────────┤
│  2. Source audio                        │
│     [Microphone]  [Importer un fichier] │
│          ◉  Enregistrement en cours…    │
├─────────────────────────────────────────┤
│  3. Génération                          │
│     [▶  Générer le compte-rendu]        │
│     ✓ Transcription vocale              │
│     ◎ Rédaction du compte-rendu…        │
├─────────────────────────────────────────┤
│  Compte-rendu                           │
│  # Compte-rendu — 23/04/2026            │
│  Projet : Résidence Les Pins            │
│  …streaming token par token…            │
└─────────────────────────────────────────┘
```

---

## Prérequis

| Composant | Version | Rôle |
|-----------|---------|------|
| Python | 3.11+ | Runtime |
| [Ollama](https://ollama.com/download/windows) | latest | Service LLM local |
| Modèle Gemma 4 | `gemma4:e4b` | Rédaction (~9 Go) |
| Modèle Whisper | `medium` | Transcription (~1.5 Go) |

> Les modèles IA se téléchargent directement depuis l'interface de l'application.

---

## Installation rapide

### 1. Cloner le dépôt

```bash
git clone https://github.com/hugo-burnet/CR_AI.git
cd CR_AI
```

### 2. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

### 3. Installer Ollama

Téléchargez et installez [Ollama pour Windows](https://ollama.com/download/windows), puis lancez-le :

```bash
ollama serve
```

### 4. Lancer l'application

```bash
python app.py
```

Le navigateur s'ouvre automatiquement sur `http://localhost:5000`.  
Si Ollama ou les modèles IA sont manquants, l'application affiche un **assistant de configuration** pour tout installer en un clic.

---

## Générer un exécutable Windows (.exe)

Pour distribuer l'application sur une machine sans Python :

```bash
build.bat
```

Le dossier `dist/CR_Chantier/` est généré. Copiez ce dossier entier sur n'importe quelle machine Windows et lancez `CR_Chantier.exe`.

> **Note :** Ollama doit être installé séparément sur chaque machine. L'application guide l'utilisateur automatiquement.

---

## Format du compte-rendu généré

```markdown
# Compte-rendu — 23/04/2026 à 14:30

Projet : Résidence Les Pins — Lot 4 Plomberie
Contexte : Réunion hebdo, problème étanchéité toiture

## Participants mentionnés
- M. Dupont (conducteur de travaux)
- M. Martin (chef de chantier)

## Contexte / Objet de la réunion
Réunion de suivi hebdomadaire portant sur l'avancement du lot plomberie...

## Points abordés
### 1. Étanchéité toiture
- Infiltration constatée en zone nord-est

## Décisions prises
| Décision | Responsable | Échéance |
|---|---|---|
| Intervention étanchéiste | M. Martin | 30/04/2026 |

## Actions à mener (To-do)
- [ ] Contacter l'étanchéiste — Responsable : M. Dupont — Délai : 25/04/2026

## Points en suspens / À clarifier
- Devis étanchéité non reçu

## Prochaine réunion
Mercredi 30/04/2026
```

---

## Architecture

```
CR_AI/
├── app.py                    # Serveur Flask — routes + pipeline IA
├── templates/
│   └── index.html            # Interface web (Tailwind CSS + marked.js)
├── compte_rendu_chantier.py  # Script CLI original (référence)
├── cr_chantier.spec          # Configuration PyInstaller
├── build.bat                 # Script de build Windows
└── requirements.txt          # Dépendances Python
```

### Stack technique

- **Backend** : Flask 3, Python 3.11+
- **Transcription** : faster-whisper (Whisper medium, CPU, int8)
- **LLM** : Ollama API locale — modèle Gemma 4 (`gemma4:e4b`)
- **Streaming** : Server-Sent Events (SSE) pour l'affichage temps réel
- **Frontend** : HTML + Tailwind CSS (CDN) + marked.js
- **Packaging** : PyInstaller (one-dir, Windows)

---

## Données & confidentialité

Aucune donnée ne quitte la machine. Tout le pipeline est 100 % local :

- Enregistrement audio → fichier temporaire local
- Transcription → CPU local via faster-whisper
- Rédaction → Ollama sur `localhost:11434`
- Sauvegarde → `~/comptes_rendus/` en local

---

## Licence

MIT — libre d'utilisation, modification et distribution.
