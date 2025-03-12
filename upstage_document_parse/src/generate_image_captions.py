# generate_image_captions.py
import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

def get_image_caption(image_path, api_key):
    # 가상의 GPT‑4V 캡션 API 엔드포인트 (실제 사용 시 OpenAI 문서를 참고하세요)
    url = "https://api.openai.com/v1/gpt-4v/caption"
    headers = {"Authorization": f"Bearer {api_key}"}
    with open(image_path, "rb") as f:
        files = {"image": f}
        response = requests.post(url, headers=headers, files=files)
    if response.status_code == 200:
        data = response.json()
        caption = data.get("caption", "")
        return caption
    else:
        print(f"캡션 API 오류 ({image_path}): {response.status_code}, {response.text}")
        return ""

def generate_captions(items_folder):
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
    
    if not os.path.exists(items_folder):
        raise FileNotFoundError(f"Items 폴더가 존재하지 않습니다: {items_folder}")
    
    print("이미지 캡션 생성 작업 시작...")
    for filename in os.listdir(items_folder):
        image_path = os.path.join(items_folder, filename)
        caption = get_image_caption(image_path, OPENAI_API_KEY)
        # {원본이미지이름}_caption.txt 로 저장
        caption_filename = os.path.join(items_folder, f"{os.path.splitext(filename)[0]}_caption.txt")
        with open(caption_filename, "w", encoding="utf-8") as f:
            f.write(caption)
        print(f"{filename} 캡션 저장 완료: {caption_filename}")
    print("이미지 캡션 생성 완료.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_image_captions.py <items_folder>")
        sys.exit(1)
    items_folder = sys.argv[1]
    generate_captions(items_folder)
