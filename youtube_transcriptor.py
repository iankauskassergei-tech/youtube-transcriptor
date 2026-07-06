#!/usr/bin/env python3
"""Скачивание YouTube-транскрипций: одно видео или batch из файла → SQLite + .txt."""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

DEFAULT_DB = "transcripts.db"
DEFAULT_OUTPUT_DIR = "transcripts"
DEFAULT_LANGUAGES = ("en", "ru")
MAX_RETRIES = 3
RETRY_DELAY_SEC = 2

VIDEO_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def extract_video_id(value: str) -> str | None:
    value = value.strip()
    if not value or value.startswith("#"):
        return None

    if VIDEO_ID_RE.match(value):
        return value

    patterns = [
        r"(?:youtube\.com/watch\?v=|youtube\.com/embed/|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return match.group(1)

    return None


def init_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transcripts (
            video_id      TEXT PRIMARY KEY,
            url           TEXT NOT NULL,
            language      TEXT,
            text          TEXT,
            word_count    INTEGER DEFAULT 0,
            status        TEXT NOT NULL DEFAULT 'pending',
            error_message TEXT,
            fetched_at    TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_transcripts_status ON transcripts(status)"
    )
    conn.commit()
    return conn


def clean_transcript_text(snippet) -> str:
    parts: list[str] = []
    for item in snippet:
        text = getattr(item, "text", str(item)).strip()
        if text:
            parts.append(text)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def fetch_transcript(api: YouTubeTranscriptApi, video_id: str, languages: tuple[str, ...]):
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return api.fetch(video_id, languages=languages)
        except (VideoUnavailable, TranscriptsDisabled, NoTranscriptFound):
            raise
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SEC * attempt)

    if last_error:
        raise last_error
    raise RuntimeError(f"Failed to fetch transcript for {video_id}")


def save_transcript(
    conn: sqlite3.Connection,
    output_dir: Path,
    video_id: str,
    url: str,
    language: str | None,
    text: str | None,
    status: str,
    error_message: str | None = None,
) -> None:
    fetched_at = datetime.now(timezone.utc).isoformat()
    word_count = len(text.split()) if text else 0

    conn.execute(
        """
        INSERT INTO transcripts (
            video_id, url, language, text, word_count, status, error_message, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET
            url = excluded.url,
            language = excluded.language,
            text = excluded.text,
            word_count = excluded.word_count,
            status = excluded.status,
            error_message = excluded.error_message,
            fetched_at = excluded.fetched_at
        """,
        (video_id, url, language, text, word_count, status, error_message, fetched_at),
    )
    conn.commit()

    if status == "success" and text:
        txt_path = output_dir / f"{video_id}.txt"
        txt_path.write_text(text, encoding="utf-8")


def process_video(
    api: YouTubeTranscriptApi,
    conn: sqlite3.Connection,
    output_dir: Path,
    raw_input: str,
    languages: tuple[str, ...],
    skip_existing: bool,
) -> str:
    video_id = extract_video_id(raw_input)
    if not video_id:
        return "skip"

    url = f"https://www.youtube.com/watch?v={video_id}"

    if skip_existing:
        row = conn.execute(
            "SELECT status FROM transcripts WHERE video_id = ? AND status = 'success'",
            (video_id,),
        ).fetchone()
        if row:
            print(f"  SKIP  {video_id} (already in database)")
            return "skipped"

    print(f"  FETCH {video_id} ...", end=" ", flush=True)

    try:
        transcript = fetch_transcript(api, video_id, languages)
        text = clean_transcript_text(transcript)
        language = getattr(transcript, "language", None) or languages[0]
        save_transcript(conn, output_dir, video_id, url, language, text, "success")
        print(f"OK ({language}, {len(text.split())} words)")
        return "success"

    except NoTranscriptFound:
        save_transcript(
            conn, output_dir, video_id, url, None, None, "no_transcript",
            "No transcript found for requested languages",
        )
        print("NO TRANSCRIPT")
        return "no_transcript"

    except TranscriptsDisabled:
        save_transcript(
            conn, output_dir, video_id, url, None, None, "disabled",
            "Transcripts are disabled for this video",
        )
        print("DISABLED")
        return "disabled"

    except VideoUnavailable:
        save_transcript(
            conn, output_dir, video_id, url, None, None, "unavailable",
            "Video is unavailable",
        )
        print("UNAVAILABLE")
        return "unavailable"

    except Exception as exc:
        save_transcript(
            conn, output_dir, video_id, url, None, None, "error", str(exc),
        )
        print(f"ERROR: {exc}")
        return "error"


def load_inputs(file_path: Path) -> list[str]:
    return file_path.read_text(encoding="utf-8").splitlines()


def print_summary(stats: dict[str, int], db_path: Path, output_dir: Path) -> None:
    total = sum(stats.values())
    print("\n" + "=" * 50)
    print(f"Done. Processed: {total}")
    for key in ("success", "skipped", "no_transcript", "disabled", "unavailable", "error", "skip"):
        if stats.get(key):
            print(f"  {key}: {stats[key]}")
    print(f"\nDatabase:  {db_path.resolve()}")
    print(f"Text files: {output_dir.resolve()}/")
    print("=" * 50)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download YouTube transcripts into SQLite and .txt files.",
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="YouTube URL or video ID",
    )
    parser.add_argument(
        "--file", "-f",
        type=Path,
        help="Text file with URLs or video IDs (one per line)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(DEFAULT_DB),
        help=f"SQLite database path (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=Path(DEFAULT_OUTPUT_DIR),
        help=f"Directory for .txt files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--languages", "-l",
        default=",".join(DEFAULT_LANGUAGES),
        help="Comma-separated language codes (default: en,ru)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip videos already successfully downloaded",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.target and not args.file:
        parser.print_help()
        return 1

    languages = tuple(lang.strip() for lang in args.languages.split(",") if lang.strip())
    args.output_dir.mkdir(parents=True, exist_ok=True)

    conn = init_db(args.db)
    api = YouTubeTranscriptApi()

    inputs: list[str] = []
    if args.file:
        if not args.file.exists():
            print(f"Error: file not found: {args.file}")
            return 1
        inputs.extend(load_inputs(args.file))
    if args.target:
        inputs.append(args.target)

    stats: dict[str, int] = {}
    print(f"Starting batch: {len(inputs)} item(s)\n")

    for raw in inputs:
        result = process_video(
            api, conn, args.output_dir, raw, languages, args.skip_existing,
        )
        stats[result] = stats.get(result, 0) + 1

    print_summary(stats, args.db, args.output_dir)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
