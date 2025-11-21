# src/collectors/yt_dlp_collector.py

import subprocess
import json
import re
from pathlib import Path
from datetime import datetime
from webvtt import WebVTT


class YTDLPTranscriptCollector:
    """
    Super-robust transcript collector using yt-dlp.
    Supports VTT, SRT, JSON3, SRV1-3, TTML, XML.
    """

    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------
    # BASIC HELPERS
    # ----------------------
    def extract_video_id(self, url: str) -> str:
        if "v=" in url:
            return url.split("v=")[1].split("&")[0]
        if "youtu.be/" in url:
            return url.split("youtu.be/")[1].split("?")[0]
        return url

    def _run(self, cmd: list):
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if proc.returncode != 0:
            print("YT-DLP FAILED")
            print("COMMAND:", " ".join(cmd))
            print("ERROR:", proc.stderr)
            raise RuntimeError(proc.stderr)

        return proc

    # ----------------------
    # DOWNLOAD SUBTITLES
    # ----------------------
    def download_subtitles(self, video_url: str):
        video_id = self.extract_video_id(video_url)

        cmd = [
            "yt-dlp",
            "--write-auto-sub",
            "--write-sub",
            "--sub-langs", "en",
            "--skip-download",
            "-o", str(self.output_dir / f"{video_id}.%(ext)s"),
            video_url,
        ]

        self._run(cmd)

        # Find ANY matching subtitle
        possible_exts = [
            "vtt", "srt", "json", "json3",
            "srv1", "srv2", "srv3",
            "ttml", "xml"
        ]

        matches = []
        for ext in possible_exts:
            matches.extend(self.output_dir.glob(f"{video_id}*.{ext}"))

        if not matches:
            raise FileNotFoundError(f"No subtitle file found for {video_id}")

        return str(matches[0])  # best guess

    # ----------------------
    # PARSERS
    # ----------------------
    def parse_vtt(self, path: str):
        segments = []
        for caption in WebVTT().read(path):
            segments.append({
                "start": caption.start,
                "end": caption.end,
                "text": caption.text.replace("\n", " ").strip()
            })
        return segments

    def parse_srt(self, path):
        segments = []
        with open(path, "r", encoding="utf-8") as f:
            blocks = re.split(r"\n\s*\n", f.read())
        for block in blocks:
            lines = block.strip().splitlines()
            if len(lines) >= 3 and "-->" in lines[1]:
                start, end = lines[1].split("-->")
                text = " ".join(lines[2:])
                segments.append({
                    "start": start.strip(),
                    "end": end.strip(),
                    "text": text.strip()
                })
        return segments

    def parse_json3(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        segments = []
        for ev in data.get("events", []):
            if "segs" not in ev:
                continue
            text = "".join(seg.get("utf8", "") for seg in ev["segs"])
            start = ev.get("tStartMs", 0) / 1000
            dur = ev.get("dDurationMs", 0) / 1000
            segments.append({
                "start": start,
                "end": start + dur,
                "text": text.strip()
            })
        return segments

    def parse_srv(self, path):
        text = Path(path).read_text(encoding="utf-8")
        segments = []

        entries = re.findall(
            r'<p[^>]*t="(\d+)"[^>]*d="(\d+)"[^>]*>(.*?)</p>',
            text, flags=re.DOTALL
        )

        for start_m, dur_m, content in entries:
            clean = re.sub(r"<.*?>", "", content).strip()
            start = int(start_m) / 1000
            end = start + (int(dur_m) / 1000)
            segments.append({
                "start": start,
                "end": end,
                "text": clean
            })

        return segments

    # ----------------------
    # METADATA
    # ----------------------
    def fetch_metadata(self, video_url: str):
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--dump-json",
            video_url
        ]

        proc = self._run(cmd)
        data = json.loads(proc.stdout)

        return {
            "title": data.get("title"),
            "channel": data.get("channel"),
            "upload_date": data.get("upload_date"),
            "duration": data.get("duration"),
            "description": data.get("description"),
            "view_count": data.get("view_count"),
            "like_count": data.get("like_count"),
            "tags": data.get("tags"),
        }

    # ----------------------
    # MAIN COLLECT METHOD
    # ----------------------
    def collect(self, video_url: str):
        video_id = self.extract_video_id(video_url)

        subtitle_path = self.download_subtitles(video_url)
        ext = subtitle_path.split(".")[-1]

        # parse transcript
        if ext == "vtt":
            transcript = self.parse_vtt(subtitle_path)
        elif ext == "srt":
            transcript = self.parse_srt(subtitle_path)
        elif ext == "json3":
            transcript = self.parse_json3(subtitle_path)
        elif ext.startswith("srv"):
            transcript = self.parse_srv(subtitle_path)
        else:
            raise ValueError(f"Unsupported subtitle format: {ext}")

        metadata = self.fetch_metadata(video_url)

        # FINAL JSON
        out_json = {
            "video_id": video_id,
            "video_url": video_url,
            "subtitle_format": ext,
            "subtitle_file": subtitle_path,
            "transcript": transcript,
            "title": metadata["title"],
            "channel": metadata["channel"],
            "upload_date": metadata["upload_date"],
            "duration": metadata["duration"],
            "description": metadata["description"],
            "views": metadata["view_count"],
            "likes": metadata["like_count"],
            "tags": metadata["tags"],
            "collected_at": datetime.utcnow().isoformat(),
        }

        save_path = self.output_dir / f"{video_id}.json"
        save_path.write_text(json.dumps(out_json, indent=2), encoding="utf-8")
        return save_path
