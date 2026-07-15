# YT to MP3 Downloader 🎵

A premium, fast, and high-fidelity YouTube to MP3 audio converter web application. Built with **Flask** and **yt-dlp**, featuring a state-of-the-art synthwave/cyberpunk glassmorphism layout, real-time download and conversion progress logging, local history saving, and Dockerized deployment configurations ready for **Render**.

---

## Key Features

- **High-Quality Audio Extraction:** Support for conversions in `128kbps`, `192kbps` (Recommended), and `320kbps` (Hi-Fi) formats.
- **Glassmorphism Aesthetic UI:** Rich synthwave dark mode interfaces featuring glowing mesh orbs, transparent glass panels, responsive grids, and micro-hover states.
- **Real-Time Progress Streaming (SSE):** Monitor both download percentages, network speeds, ETAs, and conversion statuses live via Server-Sent Events.
- **Local Download Logs:** Store recent conversions in local storage for quick access and reconversion of favorite titles.
- **Stateless Filesystem Cleans:** Local metadata lookup handles multi-process servers (e.g. Gunicorn) and automatically deletes temporary conversion caches after download or 5 minutes of inactivity.
- **Search & Preview Integration:** Resolves titles, thumbnail images, channels, and duration badges before starting the download.

---

## Local Development Installation

### Prerequisites

1. **Python 3.10+**
2. **FFmpeg** (Required to encode/transcode files to `.mp3` format)
   - **Windows:** Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html), extract, and add the `/bin` folder to your System `PATH`.
   - **macOS:** Install using brew: `brew install ffmpeg`
   - **Ubuntu/Linux:** Install using apt: `sudo apt-get install ffmpeg`

### Running the App

1. Navigate to the `yttomp3` folder in your terminal:
   ```bash
   cd yttomp3
   ```
2. Create and start a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the development server:
   ```bash
   python app.py
   ```
5. Open your web browser and navigate to: `http://localhost:5000`

---

## Deploying to Render (Hosting)

This project contains a `Dockerfile` and a `render.yaml` configuration that allows for instant Docker deployments. Using Docker is the recommended approach on Render because installing `ffmpeg` in native Python environments can be complex.

### Step 1: Push Code to GitHub

1. Initialize Git in the project root:
   ```bash
   git init
   ```
2. Create a new repository on GitHub.
3. Link your local project to the GitHub repository:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   ```
4. Stage, commit, and push the code:
   ```bash
   git add .
   git commit -m "Initialize YT to MP3 downloader"
   git branch -M main
   git push -u origin main
   ```

### Step 2: Host on Render

#### Option A: One-click Blueprint Deploy (Recommended)
1. Go to the [Render Dashboard](https://dashboard.render.com/).
2. Click **Blueprints** from the top navigation bar.
3. Click **New Blueprint Instance**.
4. Select the repository you just pushed.
5. Render will detect the `render.yaml` file, and automatically configure a Docker-based **Web Service** on the **Free tier**. Click **Approve** to deploy.

#### Option B: Manual Web Service Setup
1. Go to the [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Web Service**.
3. Choose your repository and select **Docker** as the base runtime.
4. Render will automatically read the `Dockerfile` in the root of the project to build the service.
5. Select the **Free** instance plan, modify any env profiles if required, and click **Deploy Web Service**.
