import os
import sys
import requests
import time
from dotenv import load_dotenv
from save_files import save_files  
from generate_image_captions import generate_captions

sys.dont_write_bytecode = True
load_dotenv()
UPSTAGE_API_KEY, OPENAI_API_KEY = map(os.getenv, ["UPSTAGE_API_KEY", "OPENAI_API_KEY"])

if not (UPSTAGE_API_KEY and OPENAI_API_KEY):
    raise ValueError("환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

# 전역 변수로 사용할 base_folder 선언
BASE_FOLDER = None

def preprocess_pdf(filename):
    """
    PDF 파일을 Upstage Document Parse API를 사용하여 분석하고 결과를 data 폴더에 저장한 뒤,
    그 HTML 파일을 MD로 변환하고, base_folder를 전역 변수에 저장합니다.
    API 요청부터 결과 반환까지 걸린 시간을 출력합니다.
    """
    global BASE_FOLDER
    url = "https://api.upstage.ai/v1/document-ai/document-parse"
    headers = {"Authorization": f"Bearer {UPSTAGE_API_KEY}"}

    with open(filename, "rb") as f:
        files = {"document": f}
        data = {
            "output_formats": "['html', 'text', 'markdown']",
            "ocr": "force",
            "base64_encoding": "['table']",
            "model": "document-parse"
        }
        print("╔════════════════════════════════════════")
        print(f"║ 📤 PDF 파일 {filename} 을(를) API에 업로드 중...")

        start_time = time.time()  # API 요청 시작 시간 기록
        response = requests.post(url, headers=headers, files=files, data=data)
        end_time = time.time()    # 응답 수신 후 시간 기록
        elapsed = end_time - start_time
        print(f"║ ⏱️ Upstage API 소요 시간: {elapsed:.2f}초")
    
    if response.status_code == 200:
        result = response.json()
        file_paths, images_paths, base_folder = save_files(result, filename)
        BASE_FOLDER = base_folder.replace("\\", "/")
        html_path = file_paths.get("html")


def upstage_document_parse(pdf_file_path):
    
    results = preprocess_pdf(pdf_file_path)

    # # 이미지 캡션 생성 및 MD에 캡션 병합
    generate_captions(OPENAI_API_KEY, BASE_FOLDER) 
    # merge_captions_into_md(BASE_FOLDER)

    # 오류가 없었다면 저장된 파일의 폴더경로를 반환함
    return BASE_FOLDER

if __name__ == "__main__":
    pdf_file_path = "pdf/모니터1~3p.pdf"
    upstage_document_parse(pdf_file_path)
