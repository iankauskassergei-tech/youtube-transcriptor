import sys
import json
from youtube_transcript_api import YouTubeTranscriptApi

def main():
    if len(sys.argv) < 2:
        print("Использование: python3 youtube_transcriptor.py <URL>")
        return

    url = sys.argv[1]
    video_id = url.split("v=")[-1].split("&")[0]
    
    try:
        # Пытаемся создать экземпляр без аргументов
        api = YouTubeTranscriptApi()
        
        # Вызываем fetch с передачей video_id как первого аргумента
        # Если библиотека требует 'self', она подставит его сама при таком вызове
        transcript = api.fetch(video_id, languages=['en', 'ru'])
        
        # Сохранение данных
        data = []
        for item in transcript:
            # Универсальный способ получения текста, независимо от формата объекта
            text = getattr(item, 'text', str(item))
            data.append({'text': text})
        
        with open("output.txt", "w", encoding="utf-8") as f:
            for entry in data:
                f.write(entry['text'] + '\n')
        
        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print("Успех! Файлы output.txt и output.json успешно созданы.")
        
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()