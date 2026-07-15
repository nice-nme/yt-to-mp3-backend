import os
import re
import uuid
import time
import json
import queue
import threading
from flask import Flask, render_template, request, jsonify, Response

app = Flask(__name__)

TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_downloads')
os.makedirs(TEMP_DIR, exist_ok=True)

# Helper: Clean title for windows/linux safe filename
def clean_filename(title):
    # Remove unsupported characters
    s = re.sub(r'[^\w\s-]', '', title).strip()
    s = re.sub(r'\s+', ' ', s)
    return s if s else "audio"

# Helper: Format seconds to MM:SS or H:MM:SS
def format_duration(seconds):
    if not seconds:
        return "Unknown"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

# Background thread to clean files older than 5 minutes
def clean_temp_files():
    while True:
        try:
            now = time.time()
            for filename in os.listdir(TEMP_DIR):
                file_path = os.path.join(TEMP_DIR, filename)
                if os.path.isfile(file_path):
                    # Check age: older than 300 seconds (5 mins)
                    if now - os.path.getmtime(file_path) > 300:
                        os.remove(file_path)
                        print(f"Cleaned up stale file: {filename}")
        except Exception as e:
            print(f"Error in cleanup thread: {e}")
        time.sleep(60)

# Start cleanup daemon thread
cleanup_thread = threading.Thread(target=clean_temp_files, daemon=True)
cleanup_thread.start()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/info', methods=['GET'])
def get_info():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    import yt_dlp
    ydl_opts = {
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Single video configuration
            if 'entries' in info:
                # If playlist, just use first video metadata
                video_data = info['entries'][0]
            else:
                video_data = info
                
            video_id = video_data.get('id')
            title = video_data.get('title', 'Unknown Title')
            duration = video_data.get('duration', 0)
            
            # Find best thumbnail image
            thumbnail = video_data.get('thumbnail')
            if not thumbnail and video_data.get('thumbnails'):
                thumbnail = video_data['thumbnails'][-1].get('url')
                
            channel = video_data.get('uploader', 'Unknown Channel')
            
            return jsonify({
                "id": video_id,
                "title": title,
                "duration": format_duration(duration),
                "thumbnail": thumbnail,
                "channel": channel,
                "url": url
            })
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve video details: {str(e)}"}), 500

def download_task(url, quality, file_id, q):
    import yt_dlp
    
    def prog_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            percent = 0.0
            if total > 0:
                percent = round((downloaded / total) * 100, 1)
            
            speed = d.get('speed')
            speed_str = "0 KB/s"
            if speed:
                if speed > 1024 * 1024:
                    speed_str = f"{round(speed / (1024*1024), 1)} MB/s"
                else:
                    speed_str = f"{round(speed / 1024, 1)} KB/s"
            
            eta = d.get('eta')
            eta_str = f"{eta}s" if eta else "calculating"
            
            q.put({
                "status": "downloading",
                "percent": percent,
                "speed": speed_str,
                "eta": eta_str
            })
        elif d['status'] == 'finished':
            q.put({
                "status": "downloading",
                "percent": 100.0,
                "speed": "N/A",
                "eta": "0s"
            })
            q.put({
                "status": "processing",
                "message": "Conversion starting... Please wait."
            })
            
    def pp_hook(d):
        if d['status'] == 'started' and d.get('postprocessor') == 'FFmpegExtractAudio':
            q.put({
                "status": "processing",
                "message": "Converting to MP3 format using ffmpeg..."
            })
        elif d['status'] == 'finished' and d.get('postprocessor') == 'FFmpegExtractAudio':
            q.put({
                "status": "processing",
                "message": "Post-processing complete."
            })

    output_path = os.path.join(TEMP_DIR, f"{file_id}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': quality,
        }],
        'progress_hooks': [prog_hook],
        'postprocessor_hooks': [pp_hook],
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'noplaylist': True,
    }
    
    try:
        # Check system requirements for ffmpeg
        import shutil
        if not shutil.which('ffmpeg') and not shutil.which('ffmpeg.exe'):
            raise Exception("ffmpeg is not installed on the host system. High-quality MP3 encoding is unavailable.")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get title and pull stream
            info = ydl.extract_info(url, download=True)
            if 'entries' in info:
                title = info['entries'][0].get('title', 'audio')
            else:
                title = info.get('title', 'audio')
            
            cleaned = clean_filename(title)
            
            # Write registry metadata structure to file for multi-worker support
            meta_path = os.path.join(TEMP_DIR, f"{file_id}.json")
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump({"download_name": f"{cleaned}.mp3"}, f)
                
            q.put({
                "status": "done",
                "file_id": file_id
            })
    except Exception as e:
        q.put({
            "status": "error",
            "message": str(e)
        })

@app.route('/api/stream-download')
def stream_download():
    url = request.args.get('url')
    quality = request.args.get('quality', '192')
    
    if not url:
        return Response("data: {\"status\": \"error\", \"message\": \"No URL provided\"}\n\n", mimetype='text/event-stream')
        
    file_id = str(uuid.uuid4())
    q = queue.Queue()
    
    # Run the download process in a separate thread
    t = threading.Thread(target=download_task, args=(url, quality, file_id, q))
    t.start()
    
    def generate():
        yield f"data: {json.dumps({'status': 'starting', 'message': 'Initializing download parameters...'})}\n\n"
        
        while t.is_alive() or not q.empty():
            try:
                data = q.get(timeout=0.5)
                yield f"data: {json.dumps(data)}\n\n"
            except queue.Empty:
                continue
                
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/download-file/<file_id>')
def download_file(file_id):
    # Secure validation
    if not re.match(r'^[a-f0-9\-]{36}$', file_id):
        return "Invalid File ID format", 400
        
    meta_path = os.path.join(TEMP_DIR, f"{file_id}.json")
    file_path = os.path.join(TEMP_DIR, f"{file_id}.mp3")
    
    if not os.path.exists(meta_path) or not os.path.exists(file_path):
        return "Download expired or file not found", 404
        
    try:
        with open(meta_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        download_name = metadata.get("download_name", "download.mp3")
    except Exception:
        download_name = "download.mp3"
        
    file_size = os.path.getsize(file_path)
    
    # Stream and clean
    def generate_and_delete():
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk
        finally:
            try:
                # Cleanup files
                if os.path.exists(file_path):
                    os.remove(file_path)
                if os.path.exists(meta_path):
                    os.remove(meta_path)
            except Exception as e:
                print(f"Error checking out download file: {e}")
                
    response = Response(generate_and_delete(), mimetype="audio/mpeg")
    response.headers["Content-Length"] = file_size
    
    # ASCII clean format for filename header
    ascii_download_name = download_name.encode('ascii', 'ignore').decode('ascii')
    if not ascii_download_name:
        ascii_download_name = "audio.mp3"
    response.headers["Content-Disposition"] = f'attachment; filename="{ascii_download_name}"'
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
