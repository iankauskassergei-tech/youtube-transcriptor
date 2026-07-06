# YouTube Transcriptor

Скрипт для массового скачивания транскрипций с YouTube в SQLite и текстовые файлы.

Один URL → один файл. Список из 900 URL → база + папка с `.txt` за минуты, не недели.

## Установка

```bash
pip install -r requirements.txt
```

## Использование

### Одно видео

```bash
python3 youtube_transcriptor.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Batch из файла

```bash
python3 youtube_transcriptor.py --file urls.txt
```

### Все опции

```bash
python3 youtube_transcriptor.py --file urls.txt \
  --db transcripts.db \
  --output-dir transcripts \
  --languages en,ru \
  --skip-existing
```

| Флаг | Описание |
|------|----------|
| `--file`, `-f` | Файл со списком URL или video ID (по одному на строку) |
| `--db` | Путь к SQLite базе (по умолчанию: `transcripts.db`) |
| `--output-dir`, `-o` | Папка для `.txt` файлов (по умолчанию: `transcripts/`) |
| `--languages`, `-l` | Языки через запятую (по умолчанию: `en,ru`) |
| `--skip-existing` | Пропускать уже скачанные видео |

## Что на выходе

**SQLite** (`transcripts.db`):

| Поле | Описание |
|------|----------|
| `video_id` | ID видео |
| `url` | Полная ссылка |
| `language` | Язык субтитров |
| `text` | Полный текст транскрипции |
| `word_count` | Количество слов |
| `status` | `success` / `no_transcript` / `disabled` / `unavailable` / `error` |
| `error_message` | Текст ошибки (если есть) |
| `fetched_at` | Время скачивания (UTC) |

**Текстовые файлы:** `transcripts/{video_id}.txt`

## Пример urls.txt

```
https://www.youtube.com/watch?v=jNQXAC9IVRw
https://youtu.be/ANOTHER_ID
VIDEO_ID_11CHARS
# строки с # игнорируются
```

См. также `urls.example.txt`.

## Поиск по базе

```bash
sqlite3 transcripts.db "SELECT video_id, word_count, status FROM transcripts LIMIT 10;"
sqlite3 transcripts.db "SELECT text FROM transcripts WHERE video_id = 'VIDEO_ID';"
```

## Зачем это

Типичная задача: скачать транскрипции сотен видео и сложить в базу для дальнейшей работы (поиск, саммари, RAG, контент-пайплайн).  
Руками — недели. Скриптом — минуты.
