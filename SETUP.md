# Setup Guide

## Prerequisites

- Windows 10/11
- DaVinci Resolve 18+ installed (free version works)
- Python 3.10+ installed and on PATH
- ffmpeg on PATH (required for upload audio normalization)
- Git (optional, for version control)

---

## 1. Python Environment

```bash
# Create a virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 2. requirements.txt

Create this file at the project root:

```
# Core
librosa>=0.10.0
opencv-python>=4.8.0
numpy>=1.24.0
Pillow>=10.0.0

# CLIP semantic tagging
open-clip-torch>=2.20.0
torch>=2.0.0
torchvision>=0.15.0

# SRT parsing
pysrt>=1.1.2

# CLI
typer>=0.9.0
rich>=13.0.0

# Upload
requests>=2.31.0
python-dotenv>=1.0.0
```

> **Note on torch:** If you have an NVIDIA GPU, install the CUDA version of torch instead for much faster CLIP tagging:
> `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`
> Check your CUDA version first with `nvidia-smi`.

---

## 2b. Web UI (recommended)

Everything below can be done from the browser instead of the CLI:

```powershell
python src/main.py serve        # opens http://127.0.0.1:8000  (--port, --no-browser)
```

The UI has tabs for Dashboard (stats / init DB), Library (tag folders, browse and remove clips),
Lyric Sync (tap along in the browser, writes the .srt), Build and Upload.
It listens on 127.0.0.1 only. The CLI commands below keep working.

---

## 3. DaVinci Resolve Python API Setup

Resolve ships with its own Python API but requires a specific setup on Windows.

### 3a. Find the Resolve script API
It lives here (default install):
```
C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\
```

### 3b. Set environment variables
Add these to your system environment variables (or set them in your run script):

```bat
set RESOLVE_SCRIPT_API=C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting
set RESOLVE_SCRIPT_LIB=C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll
set PYTHONPATH=%PYTHONPATH%;%RESOLVE_SCRIPT_API%\Modules
```

### 3c. Use Resolve's bundled Python for the API (alternative)
Resolve also ships Python 3.6 internally. For the API calls only, you can use:
```
C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Examples
```
Run the example scripts there first to verify your API connection works before running this project.

### 3d. Verify the connection
With Resolve open, run:
```python
import DaVinciResolveScript as dvr_script
resolve = dvr_script.scriptapp("Resolve")
print(resolve.GetProductName())  # Should print "DaVinci Resolve"
```

---

## 4. Initialize the Database

```bash
python src/main.py init-db
```

This creates `clips_db/clips.db` from `src/db/schema.sql`.

---

## 5. Tag Your First Video Pack

Point it at a folder of video files (.mp4, .mov, .avi):

```bash
python src/main.py tag --folder "D:\VideoPacka\Pack01"
```

This will take a few minutes per pack depending on clip count and whether you have a GPU.
Progress is shown per clip. Safe to interrupt and re-run — already-tagged clips are skipped.

Use `--force` to re-tag clips that are already in the database:

```bash
python src/main.py tag --folder "D:\VideoPacka\Pack01" --force
```

---

## 6. Build Your First Project

The `build` command generates FCPXML files that you import into DaVinci Resolve:

```bash
python src/main.py build \
  --song "D:\Music\mytrack.mp3" \
  --lyrics "D:\Music\mytrack.srt" \
  --vibe energic \
  --fps 30 \
  --name "mytrack_v1"
```

FCPXML files are saved to `output/` by default.

**Import into DaVinci Resolve:**
1. File → Import Timeline → Import AAF, EDL, XML… → select the `.fcpxml` file
2. Drag your song onto the audio track
3. File → Import → Subtitles → select your `.srt` file

### Additional build options

| Option | Default | Description |
|---|---|---|
| `--vibe` | *(none)* | Filter clips by vibe: `energic` or `sad`. Omit to draw from all clips equally |
| `--count N` | 1 | Generate N timeline variations in one run |
| `--output-dir PATH` | `output/` | Folder where FCPXML files are saved |
| `--same-anime` | false | Restrict all clips in an edit to the same anime (see folder structure below) |

#### Skipping the vibe filter

If you don't want to filter by vibe, simply omit `--vibe`. All tagged clips are used with equal weight:

```bash
python src/main.py build \
  --song "D:\Music\mytrack.mp3" \
  --lyrics "D:\Music\mytrack.srt" \
  --fps 30 \
  --name "mytrack_v1"
```

#### `--same-anime` folder structure

Clips must be organised under a folder named **`anime`**, with one sub-folder per show:

```
D:\Clips\
└── anime\
    ├── NarutoShippuden\
    │   ├── fight_01.mp4
    │   └── arc2\fight_02.mp4   ← sub-folders inside are fine
    ├── OnePiece\
    │   └── ep300_clip.mp4
    └── ...
```

The anime name is the folder **directly inside `anime\`**, regardless of how deep the clip file itself is nested.
When `--same-anime` is passed, one anime folder is chosen at random and only its clips are used for that timeline.

Example — generate 3 timelines, all clips from the same anime:

```bash
python src/main.py build \
  --song "D:\Music\mytrack.mp3" \
  --lyrics "D:\Music\mytrack.srt" \
  --vibe energic \
  --fps 30 \
  --name "mytrack_v1" \
  --count 3 \
  --same-anime
```

---

## 7. Database Management Commands

### View stats

```bash
python src/main.py stats
```

Shows total clip count, total hours, clips per vibe, and energy distribution.

### Re-tag a single clip

```bash
python src/main.py retag --path "D:\VideoPacka\Pack01\clip01.mp4"
```

### Remove a single clip from the DB

```bash
python src/main.py remove-clip --path "D:\VideoPacka\Pack01\clip01.mp4"
```

### Remove all clips from an anime

Removes every clip whose path contains the given name substring:

```bash
# Preview what would be deleted (no changes made)
python src/main.py remove-anime --name "Naruto" --dry-run

# Remove from DB only
python src/main.py remove-anime --name "Naruto"

# Remove from DB AND delete the files from disk (irreversible — prompts for confirmation)
python src/main.py remove-anime --name "Naruto" --delete-files
```

---

## 8. Social Upload (TikTok & Instagram Reels)

Bulk-upload all exported `.mp4` files in a folder to TikTok and/or Instagram Reels.
Audio is normalized via ffmpeg before upload so TikTok groups videos under the same original sound.

### 8a. Create developer app credentials

**TikTok:**
1. Go to [developers.tiktok.com](https://developers.tiktok.com) and create an app.
2. Request the `video.upload` scope.
3. Note your **Client Key** and **Client Secret**.

**Instagram:**
1. Go to [developers.facebook.com](https://developers.facebook.com) and create a Meta app.
2. Add the **Instagram Graph API** product.
3. Your Instagram account must be a **Business or Creator** account.
4. Note your **App ID** and **App Secret**.

### 8b. Create the config file

Copy the example and fill in your credentials:

```bash
cp config/upload_config.json.example config/upload_config.json
```

Edit `config/upload_config.json`:

```json
{
  "tiktok": {
    "client_key": "YOUR_TIKTOK_CLIENT_KEY",
    "client_secret": "YOUR_TIKTOK_CLIENT_SECRET",
    "access_token": "",
    "refresh_token": "",
    "expires_at": "",
    "open_id": ""
  },
  "instagram": {
    "app_id": "YOUR_META_APP_ID",
    "app_secret": "YOUR_META_APP_SECRET",
    "access_token": "",
    "expires_at": "",
    "ig_user_id": ""
  }
}
```

### 8c. Authenticate (run once)

```bash
# Authenticate both platforms
python src/main.py setup-upload

# Or a single platform
python src/main.py setup-upload --platform tiktok
python src/main.py setup-upload --platform instagram
```

This opens a browser OAuth flow and saves the token back to `config/upload_config.json`.

### 8d. Bulk upload

```bash
python src/main.py upload-batch \
  --folder "D:\Exports\mytrack_batch" \
  --caption "My caption #fyp #amv"
```

| Option | Default | Description |
|---|---|---|
| `--platforms` | tiktok instagram | Platforms to upload to |
| `--delay N` | 10 | Seconds between individual uploads |
| `--privacy` | public | `public`, `followers`, or `private` |
| `--skip-normalize` | false | Skip ffmpeg audio normalization |
| `--dry-run` | false | Preview uploads without making API calls |
| `--config PATH` | `config/upload_config.json` | Path to config file |

### 8e. Check upload history

```bash
python src/main.py upload-status

# Show last N entries
python src/main.py upload-status --last 50
```

Upload results are logged to `output/upload_log.jsonl`.

---

## Supported Video Formats for Tagging
`.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`

## Supported Audio Formats
`.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`
