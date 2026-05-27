# Setup Guide

## Prerequisites

- Windows 10/11
- DaVinci Resolve 18+ installed (free version works)
- Python 3.10+ installed and on PATH
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
librosa>=0.10.0
opencv-python>=4.8.0
numpy>=1.24.0
open-clip-torch>=2.20.0
torch>=2.0.0
torchvision>=0.15.0
pysrt>=1.1.2
typer>=0.9.0
rich>=13.0.0
Pillow>=10.0.0
```

> **Note on torch:** If you have an NVIDIA GPU, install the CUDA version of torch instead for much faster CLIP tagging:
> `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`

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

---

## 6. Build Your First Project

Make sure DaVinci Resolve is open, then:

```bash
python src/main.py build \
  --song "D:\Music\mytrack.mp3" \
  --lyrics "D:\Music\mytrack.srt" \
  --vibe energic \
  --fps 30 \
  --name "mytrack_v1"
```

Switch to Resolve — your project will be open and ready.

---

## Supported Video Formats for Tagging
`.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`

## Supported Audio Formats
`.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`
