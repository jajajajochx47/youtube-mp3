
import json
import mimetypes
import os
import queue
import shutil
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse


ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"
DOWNLOAD_DIR = ROOT / "downloads"
HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "3000"))

DOWNLOAD_DIR.mkdir(exist_ok=True)

jobs = {}
job_queue = queue.Queue()
job_lock = threading.Lock()
worker_started = False


def is_youtube_url(value):
    try:
        host = urlparse(value).hostname or ""
    except ValueError:
        return False

    host = host.removeprefix("www.")
    return host in {"youtube.com", "youtu.be", "music.youtube.com"}


def yt_dlp_available():
    try:
        import yt_dlp  # noqa: F401

        return True
    except ImportError:
        return False


def ffmpeg_path():
    common_paths = [
        shutil.which("ffmpeg"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ]

    for item in common_paths:
        if item and Path(item).exists():
            return item

    # Check winget packages in LOCALAPPDATA
    appdata = os.environ.get("LOCALAPPDATA")
    if appdata:
        winget_packages = Path(appdata) / "Microsoft" / "WinGet" / "Packages"
        if winget_packages.exists():
            for p in winget_packages.glob("**/ffmpeg.exe"):
                if p.is_file():
                    return str(p)

    return ""


def tools_status():
    ytdlp = yt_dlp_available()
    ffmpeg = ffmpeg_path()

    return {
        "ytDlp": ytdlp,
        "ffmpeg": bool(ffmpeg),
        "ffmpegPath": ffmpeg,
        "ready": bool(ytdlp and ffmpeg),
    }


def public_job(job):
    return {
        "id": job["id"],
        "url": job["url"],
        "status": job["status"],
        "title": job["title"],
        "progress": job["progress"],
        "error": job["error"],
        "downloadUrl": job["downloadUrl"],
        "createdAt": job["createdAt"],
        "updatedAt": job["updatedAt"],
    }


def new_job(url):
    job_id = f"{int(time.time() * 1000)}-{len(jobs) + 1}"
    job = {
        "id": job_id,
        "url": url,
        "status": "queued",
        "title": "",
        "progress": "รอคิว",
        "error": "",
        "filePath": "",
        "downloadUrl": "",
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    with job_lock:
        jobs[job_id] = job

    job_queue.put(job_id)
    start_worker()
    return job


def update_job(job_id, **changes):
    with job_lock:
        job = jobs.get(job_id)
        if not job:
            return
        job.update(changes)
        job["updatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")


def start_worker():
    global worker_started
    if worker_started:
        return

    worker_started = True
    thread = threading.Thread(target=worker_loop, daemon=True)
    thread.start()


def worker_loop():
    while True:
        job_id = job_queue.get()
        try:
            run_download(job_id)
        finally:
            job_queue.task_done()


def run_download(job_id):
    with job_lock:
        job = jobs.get(job_id)

    if not job:
        return

    tools = tools_status()
    if not tools["ready"]:
        update_job(
            job_id,
            status="failed",
            progress="ขาดเครื่องมือ",
            error="ต้องติดตั้ง yt-dlp Python package และ ffmpeg ก่อน",
        )
        return

    import yt_dlp

    update_job(job_id, status="downloading", progress="กำลังเริ่มดาวน์โหลด")

    def progress_hook(data):
        status = data.get("status")
        if status == "downloading":
            percent = data.get("_percent_str", "").strip()
            speed = data.get("_speed_str", "").strip()
            eta = data.get("_eta_str", "").strip()
            parts = [item for item in [percent, speed, f"ETA {eta}" if eta else ""] if item]
            update_job(job_id, progress=" | ".join(parts) or "กำลังดาวน์โหลด")
        elif status == "finished":
            update_job(job_id, progress="ดาวน์โหลดเสร็จ กำลังแปลงเป็น MP3")

    options = {
        "format": "bestaudio/best",
        "paths": {"home": str(DOWNLOAD_DIR)},
        "outtmpl": "%(title)s.%(ext)s",
        "noplaylist": True,
        "progress_hooks": [progress_hook],
        "ffmpeg_location": str(Path(tools["ffmpegPath"]).parent),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(job["url"], download=True)

        title = info.get("title") or "download"
        candidates = sorted(DOWNLOAD_DIR.glob("*.mp3"), key=lambda item: item.stat().st_mtime, reverse=True)
        file_path = candidates[0] if candidates else None

        if not file_path:
            raise RuntimeError("แปลงไฟล์เสร็จแล้วแต่หาไฟล์ MP3 ไม่เจอ")

        update_job(
            job_id,
            status="done",
            title=title,
            progress="เสร็จแล้ว",
            filePath=str(file_path),
            downloadUrl=f"/downloads/{file_path.name}",
        )
    except Exception as error:
        update_job(job_id, status="failed", progress="ไม่สำเร็จ", error=str(error))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, status, text, content_type="text/plain; charset=utf-8"):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/tools":
            self.send_json(200, tools_status())
            return

        if self.path == "/api/jobs":
            with job_lock:
                payload = [public_job(job) for job in jobs.values()]
            self.send_json(200, payload)
            return

        if self.path.startswith("/downloads/"):
            self.serve_download()
            return

        self.serve_static()

    def do_POST(self):
        if self.path != "/api/jobs":
            self.send_json(404, {"error": "Not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")

        try:
            body = json.loads(raw_body or "{}")
        except json.JSONDecodeError:
            self.send_json(400, {"error": "JSON ไม่ถูกต้อง"})
            return

        urls = [line.strip() for line in str(body.get("urls", "")).splitlines() if line.strip()]
        valid_urls = [url for url in urls if is_youtube_url(url)]

        if not valid_urls:
            self.send_json(400, {"error": "กรุณาใส่ลิงก์ YouTube อย่างน้อย 1 ลิงก์"})
            return

        created = [public_job(new_job(url)) for url in valid_urls]
        self.send_json(201, {"jobs": created, "ignored": len(urls) - len(valid_urls)})

    def serve_static(self):
        request_path = unquote(urlparse(self.path).path)
        if request_path == "/":
            request_path = "/index.html"

        file_path = (PUBLIC_DIR / request_path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(PUBLIC_DIR.resolve())) or not file_path.is_file():
            self.send_json(404, {"error": "Not found"})
            return

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_download(self):
        file_name = Path(unquote(urlparse(self.path).path)).name
        file_path = (DOWNLOAD_DIR / file_name).resolve()

        if not str(file_path).startswith(str(DOWNLOAD_DIR.resolve())) or not file_path.is_file():
            self.send_json(404, {"error": "File not found"})
            return

        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(file_path.name)}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"เปิดเว็บที่ http://{HOST}:{PORT}")
    print("กด Ctrl+C เพื่อหยุด")
    server.serve_forever()
