<div align="center">

![StreaMonitor](./logo.svg)

**A Python3 application for monitoring and saving (mostly adult) live streams from various websites.**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://hub.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-axsddlr/StreaMonitor-181717.svg?logo=github)](https://github.com/axsddlr/StreaMonitor)

Inspired by [Recordurbate](https://github.com/oliverjrose99/Recordurbate)

</div>

---

## Table of Contents

- [Features](#features)
- [Supported Sites](#supported-sites)
- [Quick Start](#quick-start)
- [Requirements](#requirements)
- [Usage](#usage)
  - [Console Commands](#starting-and-console)
  - [Remote Controller](#remote-controller)
  - [Web Interface](#web-interface)
- [Docker Support](#docker-support)
- [Configuration](#configuration)
- [Disclaimer](#disclaimer)

---

## Features

✅ **Multi-Platform Support** - 13+ streaming platforms (Chaturbate, StripChat, BongaCams, and more)
✅ **Web Dashboard** - Modern web interface for easy management
✅ **Docker Ready** - Pre-configured Docker & docker-compose setup
✅ **Resolution Selection** - Choose your preferred video quality
✅ **Auto-Recording** - Automatically starts recording when streamers go live
✅ **Multiple Interfaces** - CLI, Web UI, and ZeroMQ remote control
✅ **FFmpeg Powered** - Reliable video recording and processing

---

## Supported Sites
| Site name     | Abbreviation | Aliases                     | Quirks                 | Selectable resolution |
|---------------|--------------|-----------------------------|------------------------|-----------------------|
| Bongacams     | `BC`         |                             |                        | Yes                   |
| Cam4          | `C4`         |                             |                        | Yes                   |
| Cams.com      | `CC`         |                             |                        | Currently only 360p   |
| CamSoda       | `CS`         |                             |                        | Yes                   |
| Chaturbate    | `CB`         |                             |                        | Yes                   |
| DreamCam      | `DC`         |                             |                        | No                    |
| DreamCam VR   | `DCVR`       |                             | for VR videos          | No                    |
| FanslyLive    | `FL`         |                             |                        | Yes                   |
| Flirt4Free    | `F4F`        |                             |                        | Yes                   |
| MyFreeCams    | `MFC`        |                             |                        | Yes                   |
| SexChat.hu    | `SCHU`       |                             | use the id as username | No                    |
| StreaMate     | `SM`         | PornHubLive, PepperCams,... |                        | Yes                   |
| StripChat     | `SC`         | XHamsterLive,...            |                        | Yes                   |
| StripChat VR  | `SCVR`       |                             | for VR videos          | No                    |
| XLoveCam      | `XLC`        |                             |                        | No                    |

Currently not supported:
* Amateur.TV (They use Widevine now)
* Cherry.tv (They switched to Agora)
* ImLive (Too strict captcha protection for scraping)
* LiveJasmin (No nudity in free streams)
* ManyVids Live (They switched to Agora)

There are hundreds of clones of the sites above, you can read about them on [this site](https://adultwebcam.site/clone-sites-by-platform/).

## Quick Start

### With Docker (Recommended)
```bash
# Clone the repository
git clone https://github.com/axsddlr/StreaMonitor.git
cd StreaMonitor

# Start with docker-compose
docker-compose up -d

# Access web interface at http://localhost:5000
```

### Without Docker
```bash
# Clone the repository
git clone https://github.com/axsddlr/StreaMonitor.git
cd StreaMonitor

# Install dependencies
pip install -r requirements.txt

# Run the application
python3 Downloader.py

# Access web interface at http://localhost:5000
```

## Requirements

### System Requirements
- **Python 3.12+** (Python 3.8+ may work but not tested)
- **FFmpeg** - Must be installed and available in PATH
- **5GB+ disk space** - For recordings

### Python Dependencies
All dependencies are listed in [requirements.txt](requirements.txt):
- Flask (Web interface)
- requests (HTTP client)
- BeautifulSoup4 (HTML parsing)
- FFmpy (FFmpeg wrapper)
- m3u8 (HLS playlist parser)
- And more...

Install with:
```bash
pip install -r requirements.txt
```

## Usage

The application has the following interfaces:
* Console
* External console via ZeroMQ (sort of working)
* Web interface

#### Starting and console
Start the downloader (it does not fork yet)\
Automatically imports all streamers from the config file.
```
python3 Downloader.py
```

On the console you can use the following commands:
```
add <username> <site> - Add streamer to the list (also starts monitoring)
remove <username> [<site>] - Remove streamer from the list
start <username> [<site>] - Start monitoring streamer
start * - Start all
stop <username> [<site>] - Stop monitoring
stop * - stop all
status - Status display 
status2 - A slightly more readable status table
quit - Clean exit (Pressing CTRL-C also behaves like this)
```
For the `username` input, you usually have to enter the username as represented in the original URL of the room. 
Some sites are case-sensitive.

For the `site` input, you can use either the full or the short format of the site name. (And it is case-insensitive)

#### "Remote" controller
Add or remove a streamer to record (Also saves config file)
```
python3 Controller.py add <username> <website>
python3 Controller.py remove <username>
```

Start/stop recording streamers
```
python3 Controller.py <start|stop> <username>
```

List the streamers in the config
```
python3 Controller.py status
```

#### Web interface

You can access the web interface on port 5000. 
If set password in parameters.py username is admin, password admin, empty password is also allowed.
When you set the WEBSERVER_HOST it is also accesible to from other computers in the network

## Docker Support

### Quick Start with Docker

**Pull from GitHub Container Registry:**
```bash
docker pull ghcr.io/axsddlr/streamonitor:latest
```

**Run with docker-compose** (Recommended):
```bash
docker-compose up -d
```

**Run with Docker:**
```bash
docker run -d \
  -p 5000:5000 \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/config.json:/app/config.json \
  -e STRMNTR_HOST=0.0.0.0 \
  ghcr.io/axsddlr/streamonitor:latest
```

The web interface will be available at `http://localhost:5000`

### Environment Variables

Configure via environment variables (see [parameters.py](parameters.py) for all options):

| Variable | Default | Description |
|----------|---------|-------------|
| `STRMNTR_HOST` | `127.0.0.1` | Web server bind address (use `0.0.0.0` for remote access) |
| `STRMNTR_PORT` | `5000` | Web server port |
| `STRMNTR_PASSWORD` | `admin` | Web interface password (username: admin) |
| `STRMNTR_RESOLUTION` | `1080` | Preferred video resolution |
| `STRMNTR_CONTAINER` | `mp4` | Output container format |
| `STRMNTR_SKIN` | `truck-kun` | Web UI theme (truck-kun, shaftoverflow, kseen715) |

## Configuration

You can set some parameters in the [parameters.py](parameters.py).

## Disclaimer

> [!WARNING]
> **Educational and Proof of Concept Only**
>
> This program is a proof of concept and educational project. The author does not encourage its use for any purpose.
>
> **Important Legal and Ethical Considerations:**
> - Most (if not all) streaming platforms prohibit recording content without permission
> - Respect content creators' wishes and platform terms of service
> - **Do not publish, share, or distribute** any recordings made with this tool
> - Recording or sharing content without permission may result in **legal consequences**
> - **Do not use this tool for commercial purposes or monetization**
> - You are solely responsible for your use of this software
>
> By using this software, you acknowledge that you understand and accept these terms and take full responsibility for your actions.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Inspired by [Recordurbate](https://github.com/oliverjrose99/Recordurbate)
- Built with Python, Flask, and FFmpeg
- Community contributors and testers
