from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp, imageio_ffmpeg, threading, time, uuid, urllib.request
from yt_dlp.utils import download_range_func
from pathlib import Path
from io import BytesIO

app = Flask(__name__)
DOWNLOAD_FOLDER = Path("web_downloads").resolve()
DOWNLOAD_FOLDER.mkdir(exist_ok=True)
TASKS = {}

BASE_OPTS = {
    'quiet': True,
    'cookiefile': 'cookies.txt',
    'noplaylist': True,
    'socket_timeout': 15
}

def fmt_dur(s):
    if not s: return "Short/Live"
    m, s = divmod(int(s), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def parse_sec(t):
    if not t or not t.strip(): return None
    return sum(int(x) * (60 ** i) for i, x in enumerate(reversed(t.strip().split(":"))))

@app.route("/", methods=["GET", "POST"])
def index():
    url, info, error = "", None, None
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        try:
            with yt_dlp.YoutubeDL(BASE_OPTS) as ydl:
                d = ydl.extract_info(url, download=False)
                s_url = next((f.get("url", "") for f in reversed(d.get("formats", [])) if f.get("ext") == "mp4" and f.get("acodec") != "none" and f.get("vcodec") != "none"), "")
                info = {"title": d.get("title", "Video"), "thumbnail": d.get("thumbnail", ""), "uploader": d.get("uploader", "Creator"), "duration": fmt_dur(d.get("duration")), "stream_url": s_url}
        except Exception as e:
            error = str(e)
    return render_template("index.html", url=url, info=info, error=error)

@app.route("/download_thumb")
def download_thumb():
    try:
        req = urllib.request.Request(request.args.get("url", ""), headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            return send_file(BytesIO(r.read()), mimetype="image/jpeg", as_attachment=True, download_name=f"thumb_{int(time.time())}.jpg")
    except Exception as e:
        return str(e), 500

def run_dl(tid, url, q, s_t, e_t):
    fmts = {"1":"bv*[height<=1080]+ba/b[height<=1080]/b","2":"bv*[height<=720]+ba/b[height<=720]/b","3":"bv*[height<=480]+ba/b[height<=480]/b","4":"bv*[height<=360]+ba/b[height<=360]/b","5":"ba/b"}
    def hook(d):
        if d['status'] == 'downloading':
            tot = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            pct = int(d.get('downloaded_bytes', 0)*100/tot) if tot else 50
            TASKS[tid].update({"percent": pct, "status": "Downloading...", "speed": d.get('_speed_str', '--').strip()})
        elif d['status'] == 'finished':
            TASKS[tid].update({"percent": 95, "status": "Finalizing...", "speed": "Almost done"})
    opts = {
        **BASE_OPTS,
        'format': fmts.get(q, "bv*[height<=720]+ba/b"),
        'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
        'merge_output_format': 'mp4',
        'outtmpl': str(DOWNLOAD_FOLDER / f'%(title)s_{int(time.time())}.%(ext)s'),
        'progress_hooks': [hook]
    }
    s_sec, e_sec = parse_sec(s_t), parse_sec(e_t)
    if s_sec is not None or e_sec is not None:
        opts['download_ranges'] = download_range_func(None, [(s_sec or 0, e_sec or 999999)])
        opts['force_keyframes_at_cuts'] = True
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            i = ydl.extract_info(url, download=True)
            p = Path(ydl.prepare_filename(i))
            if q != "5" and p.with_suffix(".mp4").exists(): p = p.with_suffix(".mp4")
        TASKS[tid].update({"percent": 100, "status": "Sending...", "speed": "Done", "done": True, "filepath": str(p)})
    except Exception as e:
        TASKS[tid].update({"done": True, "error": str(e), "status": "Failed"})

@app.route("/start_download", methods=["POST"])
def start_dl():
    d = request.get_json(); tid = str(uuid.uuid4())
    TASKS[tid] = {"percent": 0, "status": "Starting...", "speed": "--", "done": False, "filepath": "", "error": ""}
    threading.Thread(target=run_dl, args=(tid, d["url"], d["quality"], d.get("start",""), d.get("end","")), daemon=True).start()
    return jsonify({"task_id": tid})

@app.route("/progress/<tid>")
def prog(tid):
    return jsonify(TASKS.get(tid, {"done": True, "error": "Not found"}))

@app.route("/get_file/<tid>")
def get_file(tid):
    t = TASKS.get(tid)
    return send_file(t["filepath"], as_attachment=True) if (t and t.get("filepath") and Path(t["filepath"]).exists()) else ("Not found", 404)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
