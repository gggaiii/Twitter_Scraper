import pytesseract
from PIL import Image
import unicodedata
import re
import os
import json

def clean_text_readable(text):
    text = unicodedata.normalize("NFKC", text)  # Normalize Unicode characters
    text = re.sub(r"[^A-Za-z0-9.,'!?©\-\s]", "", text)  # Keep only letters, numbers, and punctuation
    text = re.sub(r"\s+", " ", text).strip()  # Remove extra spaces and newlines
    return text

def __main__():
    folder_path = "/Users/y/Desktop/DATA ADS 70202/codes/twitter_scraper/results/Manchester Job Fair/media"
    result = [{"filename": filename, "text": clean_text_readable(pytesseract.image_to_string(Image.open(os.path.join(folder_path, filename))))} 
              for filename in os.listdir(folder_path) if filename.endswith(".jpg")]
    result = [record for record in result if record['text'].strip() != '']
    print(json.dumps(result, indent=4, ensure_ascii=False))

    result_path = "/Users/y/Desktop/DATA ADS 70202/codes/twitter_scraper/results/Manchester Job Fair/result.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    __main__()