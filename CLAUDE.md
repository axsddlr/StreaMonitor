# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Start the main downloader (loads config.json on startup)
python3 Downloader.py

# Remote controller (communicates via ZeroMQ)
python3 Controller.py add <username> <site>
python3 Controller.py remove <username>
python3 Controller.py <start|stop> <username>
python3 Controller.py status

# Docker
docker-compose up
```

The web UI is available at `http://127.0.0.1:5000` (credentials: admin / value of `STRMNTR_PASSWORD`).

There is no test suite in this codebase.

## Configuration

All runtime parameters are in `parameters.py`, controlled via environment variables or a `.env` file:

| Env var | Default | Description |
|---|---|---|
| `STRMNTR_DOWNLOAD_DIR` | `downloads` | Output folder |
| `STRMNTR_MIN_FREE_SPACE` | `5.0` | Min disk % before stopping |
| `STRMNTR_RESOLUTION` | `1080` | Preferred height |
| `STRMNTR_RESOLUTION_PREF` | `closest` | `exact`, `exact_or_least_higher`, `exact_or_highest_lower`, `closest` |
| `STRMNTR_CONTAINER` | `mp4` | Output container (`mp4` or `mkv`) |
| `STRMNTR_FFMPEG_READRATE` | `1.3` | ffmpeg `-readrate` |
| `STRMNTR_SEGMENT_TIME` | None | Split recordings into segments (seconds or `hh:mm:ss`) |
| `STRMNTR_HOST` | `127.0.0.1` | Web server bind address |
| `STRMNTR_PORT` | `5000` | Web server port |
| `STRMNTR_SKIN` | `truck-kun` | Web UI skin (`truck-kun`, `shaftoverflow`, `kseen715`) |
| `STRMNTR_DEBUG` | `False` | Enables debug logging and ffmpeg stderr logs |
| `STRMNTR_PASSWORD` | `admin` | Web UI password (empty = no auth) |

StripChat requires a `stripchat_mouflon_keys.json` file containing decryption keys.

## Supported Sites

| Site | Slug | Notes |
|---|---|---|
| Bongacams | `BC` | |
| Cam4 | `C4` | |
| Cams.com | `CC` | Currently only 360p |
| CamSoda | `CS` | |
| Chaturbate | `CB` | |
| DreamCam | `DC` | |
| DreamCam VR | `DCVR` | VR; uses fmp4s/WebSocket downloader |
| FanslyLive | `FL` | |
| Flirt4Free | `F4F` | |
| MyFreeCams | `MFC` | |
| SexChat.hu | `SCHU` | Use numeric room ID as username; bulk_update |
| StreaMate | `SM` | Aliases: PornHubLive, PepperCams, etc. |
| StripChat | `SC` | Aliases: XHamsterLive, etc.; requires mouflon keys; bulk_update |
| StripChat VR | `SCVR` | VR; uses fmp4s/WebSocket downloader |
| XLoveCam | `XLC` | |

Sites in `streamonitor/sites/` that are no longer functional: `amateurtv.py` (Widevine), `cherrytv.py` (Agora), `manyvids.py` (Agora).

## Architecture

### Core threading model

Each monitored streamer runs as a `Bot` (subclass of `Thread`) defined in `streamonitor/bot.py`. The main loop in `Bot.run()` polls `getStatus()` and calls `getVideoUrl()` + `getVideo()` when a stream goes public. `getVideo` is set to `getVideoFfmpeg` by default, `getVideoNativeHLS` for sites needing custom HLS segment decryption (e.g., StripChat's mouflon XOR), or `getVideoWSSVR` for VR sites streaming over WebSocket (fmp4s:// protocol).

### Site implementations

Each supported site is a class in `streamonitor/sites/` that inherits from `Bot` or `RoomIdBot`. Sites must define:
- `site` — full site name (e.g., `'StripChat'`)
- `siteslug` — short abbreviation (e.g., `'SC'`)
- `getStatus()` — returns a `Status` enum value
- `getVideoUrl()` — returns the stream URL when live

`RoomIdBot` (also in `bot.py`) extends `Bot` with room ID resolution logic; subclasses implement `getRoomIdFromUsername()` and `getUsernameFromRoomId()`. Used by StripChat, SexChat.hu, and others. The `room_id` is persisted in `config.json` and restored on startup.

Sites with `bulk_update = True` and a `getStatusBulk(streamers)` classmethod are handled by `BulkStatusManager` (polls every 10s) instead of per-bot polling — used by StripChat and SexChat.hu.

All site classes auto-register into `LOADED_SITES` (a module-level set in `bot.py`) via `__init_subclass__`. The `streamonitor/sites/__init__.py` import in `Downloader.py` triggers this registration.

### Managers

`Downloader.py` starts these managers as daemon threads:
- `BulkStatusManager` — batch-polls sites that support it
- `OOSDetector` — stops recording when disk space falls below threshold
- `CLIManager` — reads stdin commands (skipped in Docker)
- `ZMQManager` — ZeroMQ-based remote control (used by `Controller.py`)
- `HTTPManager` — Flask web server on port 5000

All managers inherit from `Manager` (in `streamonitor/manager.py`) which implements shared commands: `do_add`, `do_remove`, `do_start`, `do_stop`, `do_restart`, `do_status`, `do_status2`.

### Web UI

`HTTPManager` runs Flask with Jinja2 templates. The UI uses HTMX for partial page updates — most routes return rendered template fragments, not full pages. Three skins exist under `streamonitor/managers/httpmanager/skins/`. Static assets (Bootstrap 5, FontAwesome 6, HTMX) are vendored locally.

### Persistent state

`config.json` is the only persistent state — it stores a list of streamer objects (username, site, running flag, and site-specific fields like `room_id`). `config.loadStreamers()` reads it at startup; `Manager.saveConfig()` writes it after every add/remove/start/stop.

### Downloader backends

- `streamonitor/downloaders/ffmpeg.py` — default; wraps ffmpeg subprocess, supports `-readrate`, `-segment_time`, cookies
- `streamonitor/downloaders/hls.py` — native Python HLS segment downloader using pycurl (preferred) or requests; used when custom m3u8 processing is needed (e.g., StripChat's mouflon XOR decryption); post-processes the raw `.ts` file through ffmpeg
- `streamonitor/downloaders/fmp4s_wss.py` — WebSocket-based fMP4 downloader for VR sites (DreamCam VR, StripChat VR); receives binary fMP4 segments over WSS, then remuxes via ffmpeg

### Adding a new site

1. Create `streamonitor/sites/mysite.py` with a class inheriting `Bot` or `RoomIdBot`
2. Set `site`, `siteslug`, and optionally `aliases = [...]`
3. Implement `getStatus()` and `getVideoUrl()`
4. Import the module in `streamonitor/sites/__init__.py`
