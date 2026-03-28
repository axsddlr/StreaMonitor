# StreaMonitor

A Python 3 application for monitoring and saving live streams from various websites.

## Supported Sites

| Site | Slug | Aliases | Notes |
|---|---|---|---|
| Bongacams | `BC` | | |
| Cam4 | `C4` | | |
| Cams.com | `CC` | | Currently only 360p |
| CamSoda | `CS` | | |
| Chaturbate | `CB` | | |
| DreamCam | `DC` | | |
| DreamCam VR | `DCVR` | | VR streams |
| FanslyLive | `FL` | | |
| Flirt4Free | `F4F` | | |
| MyFreeCams | `MFC` | | |
| SexChat.hu | `SCHU` | | Use the numeric room ID as the username |
| StreaMate | `SM` | PornHubLive, PepperCams, … | |
| StripChat | `SC` | XHamsterLive, … | Requires `stripchat_mouflon_keys.json` |
| StripChat VR | `SCVR` | | VR streams |
| XLoveCam | `XLC` | | |

## Requirements

- Python 3.11+
- FFmpeg (must be on `PATH`, or set `STRMNTR_FFMPEG_PATH`)
- Node.js 20+ and npm (only needed to build the web UI from source)

## Running — Quick Start

### Option A: Docker (recommended)

1. Create the required files if they don't exist:

```bash
echo '[]' > config.json
echo '{}' > stripchat_mouflon_keys.json
```

2. Start the container:

```bash
docker-compose up -d
```

3. Open the web UI at `http://localhost:5000`. Default password: `admin`.

To stop: `docker-compose down`

---

### Option B: Run from source (Python)

**1. Install Python dependencies**

```bash
pip install -r requirements.txt
```

> On Linux you may need `libcurl` development headers for pycurl:
> `sudo apt install libcurl4-openssl-dev libssl-dev`

**2. Build the web UI**

```bash
cd frontend
npm install
npm run build
cd ..
```

This compiles the React frontend into `streamonitor/managers/httpmanager_v2/static/`.
Only needed once (or after frontend changes).

**3. Configure (optional)**

Copy `.env.example` to `.env` and edit, or set environment variables directly.
The most common settings:

```bash
STRMNTR_PASSWORD=mysecretpassword   # Web UI password (default: admin)
STRMNTR_DOWNLOAD_DIR=downloads      # Where recordings are saved
STRMNTR_HOST=127.0.0.1              # Bind address (use 0.0.0.0 for network access)
STRMNTR_PORT=5000                   # Web UI port
```

**4. Create required files**

```bash
echo '[]' > config.json
echo '{}' > stripchat_mouflon_keys.json
```

**5. Start the downloader**

```bash
python3 Downloader.py
```

The web UI will be available at `http://127.0.0.1:5000`.
Log in with username `admin` and the value of `STRMNTR_PASSWORD` (default: `admin`).

---

### Option C: Frontend development mode

Run the backend and frontend dev server separately for hot-reload:

**Terminal 1 — Backend:**
```bash
python3 Downloader.py
```

**Terminal 2 — Frontend dev server:**
```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`. API calls and WebSocket are proxied to the backend on port 5000.

---

## Console Commands

When running directly (not in Docker), the console accepts commands:

```
add <username> <site>          Add streamer and start monitoring
remove <username> [<site>]     Remove streamer
start <username> [<site>]      Start monitoring a streamer
start *                        Start all
stop <username> [<site>]       Stop monitoring a streamer
stop *                         Stop all
status                         Show status table
quit                           Clean exit (Ctrl-C also works)
```

`<site>` accepts both the full name (e.g. `StripChat`) and the short slug (e.g. `SC`), case-insensitive.

## Remote Controller

```bash
python3 Controller.py add <username> <site>
python3 Controller.py remove <username>
python3 Controller.py start <username>
python3 Controller.py stop <username>
python3 Controller.py status
```

Communicates with the running `Downloader.py` process via ZeroMQ.

## Configuration Reference

All settings can be set via environment variables or a `.env` file in the project root.

| Variable | Default | Description |
|---|---|---|
| `STRMNTR_DOWNLOAD_DIR` | `downloads` | Output folder for recordings |
| `STRMNTR_MIN_FREE_SPACE` | `5.0` | Stop recording when disk free % drops below this |
| `STRMNTR_RESOLUTION` | `1080` | Target stream height in pixels |
| `STRMNTR_RESOLUTION_PREF` | `closest` | How to pick resolution: `exact`, `exact_or_least_higher`, `exact_or_highest_lower`, `closest` |
| `STRMNTR_CONTAINER` | `mp4` | Output container (`mp4` or `mkv`) |
| `STRMNTR_FFMPEG_PATH` | `ffmpeg` | Path to the ffmpeg binary |
| `STRMNTR_FFMPEG_READRATE` | `1.3` | ffmpeg `-readrate` value |
| `STRMNTR_SEGMENT_TIME` | *(none)* | Split recordings: seconds or `hh:mm:ss` (e.g. `3600` or `1:00:00`) |
| `STRMNTR_HOST` | `127.0.0.1` | Web server bind address (`0.0.0.0` for network access) |
| `STRMNTR_PORT` | `5000` | Web server port |
| `STRMNTR_PASSWORD` | `admin` | Web UI password (set to empty string to disable auth) |
| `STRMNTR_DEBUG` | `False` | Enable verbose logging and ffmpeg stderr output |

## StripChat Setup

StripChat streams are encrypted. You must supply decryption keys in `stripchat_mouflon_keys.json`. Without this file the application will fail to start. An empty file (`{}`) is valid if you don't use StripChat.

## Docker Compose Reference

The `docker-compose.yml` includes the most common configuration options as commented-out examples:

```yaml
environment:
  STRMNTR_HOST: '0.0.0.0'          # required to access UI from outside the container
  STRMNTR_PASSWORD: 'mysecret'      # change the default password
  STRMNTR_STATUS_FREQ: "5"          # recording page status refresh interval (seconds)
  STRMNTR_LIST_FREQ: "30"           # main page streamer list refresh interval (seconds)

volumes:
  - ./downloads:/app/downloads               # where recordings are stored on the host
  - ./config.json:/app/config.json           # streamer list (persistent)
  - ./stripchat_mouflon_keys.json:/app/stripchat_mouflon_keys.json

ports:
  - '5000:5000'
```

To build the image locally instead of pulling it:

```bash
# Uncomment the build/image lines in docker-compose.yml, then:
docker-compose build
docker-compose up -d
```

## Disclaimer

This program is a proof of concept and educational project. Most streamers disallow recording. Please respect their wishes. Do not publish or share any recordings. Do not use this tool for monetization.
