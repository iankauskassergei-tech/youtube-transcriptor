# YouTube Transcript Batch Processor

A Python command-line tool for collecting YouTube transcripts and saving them as structured SQLite records and individual text files.

The tool can process a single video or a large list of URLs, helping replace repetitive manual transcript collection with an automated workflow.

## Features

- Process a single YouTube URL or video ID
- Batch-process URLs from a text file
- Retrieve English and Russian transcripts
- Save structured results to SQLite
- Export each transcript as a separate `.txt` file
- Skip previously processed videos
- Record unavailable, disabled, or failed transcripts
- Prepare datasets for search, summarization, RAG, and content workflows

## Installation

```bash
git clone https://github.com/iankauskassergei-tech/youtube-transcriptor.git
cd youtube-transcriptor
pip install -r requirements.txt
```

## Usage

### Process one video

```bash
python3 youtube_transcriptor.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Process a list of videos

Create a file named `urls.txt` containing one URL or video ID per line:

```text
https://www.youtube.com/watch?v=jNQXAC9IVRw
https://youtu.be/ANOTHER_ID
VIDEO_ID_11CHARS
```

Run:

```bash
python3 youtube_transcriptor.py --file urls.txt
```

### Advanced options

```bash
python3 youtube_transcriptor.py --file urls.txt \
  --db transcripts.db \
  --output-dir transcripts \
  --languages en,ru \
  --skip-existing
```

| Option | Description |
|---|---|
| `--file`, `-f` | Text file containing URLs or video IDs |
| `--db` | SQLite database path |
| `--output-dir`, `-o` | Directory for exported `.txt` files |
| `--languages`, `-l` | Preferred transcript languages |
| `--skip-existing` | Skip videos already stored in the database |

## Output

The SQLite database stores:

| Field | Description |
|---|---|
| `video_id` | YouTube video ID |
| `url` | Full video URL |
| `language` | Transcript language |
| `text` | Complete transcript |
| `word_count` | Transcript word count |
| `status` | Processing result |
| `error_message` | Error details when applicable |
| `fetched_at` | UTC processing timestamp |

Individual transcripts are also saved as:

```text
transcripts/{video_id}.txt
```

## Example database queries

```bash
sqlite3 transcripts.db \
  "SELECT video_id, word_count, status FROM transcripts LIMIT 10;"
```

```bash
sqlite3 transcripts.db \
  "SELECT text FROM transcripts WHERE video_id = 'VIDEO_ID';"
```

## Use cases

- Preparing transcript datasets
- Content research and analysis
- Search and summarization
- RAG knowledge bases
- Automated content-processing pipelines

## Tech stack

- Python
- SQLite
- YouTube Transcript API
