from flask import Flask, request, send_file
import yt_dlp
import os
import time

app = Flask(__name__)

@app.route('/convert', methods=['GET'])
def convert():
    url = request.args.get('url')
    if not url:
        return "Missing URL", 400

    filename = f"audio_{int(time.time())}"
    output_path = f"/tmp/{filename}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_path,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        actual_file = f"{output_path}.mp3"
        return send_file(actual_file, as_attachment=True)
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)