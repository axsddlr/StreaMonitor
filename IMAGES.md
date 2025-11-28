# StreaMonitor Image Assets

This directory contains SVG image assets for the StreaMonitor project.

## Files

### 1. `logo.svg` (1200x300)
**Purpose**: README header banner
**Usage**:
```markdown
![StreaMonitor](./logo.svg)
```

### 2. `social-preview.svg` (1280x640)
**Purpose**: GitHub repository social preview
**Usage**: Upload as PNG to Repository Settings → Social Preview

### 3. `icon.svg` (512x512)
**Purpose**: App icon, favicon
**Usage**: Convert to PNG/ICO for various sizes

## Converting SVG to PNG

### Online Tools (Easiest)
1. **CloudConvert**: https://cloudconvert.com/svg-to-png
   - Upload SVG
   - Set dimensions
   - Download PNG

2. **SVG to PNG Converter**: https://svgtopng.com/
   - Drag and drop
   - Choose size
   - Download

### Command Line (Inkscape)
```bash
# Install Inkscape first
# Windows: choco install inkscape
# Mac: brew install inkscape
# Linux: apt install inkscape

# Convert to PNG
inkscape logo.svg --export-filename=logo.png --export-width=1200
inkscape social-preview.svg --export-filename=social-preview.png --export-width=1280
inkscape icon.svg --export-filename=icon-512.png --export-width=512
inkscape icon.svg --export-filename=icon-256.png --export-width=256
inkscape icon.svg --export-filename=icon-128.png --export-width=128
```

### Command Line (ImageMagick)
```bash
# Install ImageMagick first
convert logo.svg logo.png
convert social-preview.svg social-preview.png
convert icon.svg -resize 512x512 icon-512.png
convert icon.svg -resize 256x256 icon-256.png
convert icon.svg -resize 128x128 icon-128.png
```

## Setting GitHub Social Preview

1. Convert `social-preview.svg` to PNG (1280x640)
2. Go to your GitHub repository
3. Click **Settings**
4. Scroll to **Social preview**
5. Click **Edit** → **Upload an image**
6. Upload the `social-preview.png`
7. Click **Save**

## Color Palette

- **Primary Gradient**: `#667eea` → `#764ba2` (Purple gradient)
- **Accent**: `#ef4444` (Red recording indicator)
- **Text**: White with gradient overlay
- **Background elements**: Semi-transparent white

## Design Elements

- **Recording dot**: Pulsing red circle (indicates live recording)
- **Play button**: White triangle (streaming/video playback)
- **Monitor frame**: Rectangle representing screen/monitoring
- **Signal waves**: Animated arcs (streaming broadcast)
- **Activity graph**: Line chart (monitoring data)
- **Tech badges**: Python, Docker, FFmpeg

## Customization

All SVG files can be edited in:
- **Vector editors**: Inkscape (free), Adobe Illustrator, Figma
- **Text editors**: VSCode, any text editor (SVG is XML)

To change colors, search for hex codes and replace:
- `#667eea` - Primary purple
- `#764ba2` - Secondary purple
- `#ef4444` - Recording red
