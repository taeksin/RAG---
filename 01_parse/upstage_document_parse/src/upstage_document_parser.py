# upstage-document_parser.py 

# parse하는 main코드
# UPSTAGE에 api요청을 보내고 result를 받아서 여러 함수들을 실행하는 역할

import os
import sys
import fitz
import requests
import concurrent.futures
from dotenv import load_dotenv
from datetime import datetime
from save_files import save_files  
from html_to_md import html_to_md
from split_pdf import split_pdf  # PDF 분할 함수 임포트

# merge_outputs 모듈 임포트 (merge_outputs.py 파일에 정의되어 있음)
from merge_outputs import merge_outputs
# generate_image_captions 모듈에서 캡션 생성 함수를 임포트
from generate_image_captions import generate_captions
# merge_markdown_captions 오듈에서 이미지에 캡션을 추가함
from merge_markdown_captions import merge_captions_into_md
    
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
        response = requests.post(url, headers=headers, files=files, data=data)

    if response.status_code == 200:
        result = response.json()
        file_paths, images_paths, base_folder = save_files(result, filename)
        BASE_FOLDER = base_folder.replace("\\", "/")
        html_path = file_paths.get("html")
        if html_path:
            new_md_path = html_to_md(html_path, images_paths)
        return file_paths, images_paths, base_folder
    else:
        error_msg = f"❌ API 요청 실패: {response.status_code}, {response.text}"
        print(error_msg)
        return {}, []


def upstage_document_parse(pdf_file_path):
    # 사용 예시: PDF 파일이 100페이지 이상이면 분할 후 각각 파싱하고,
    # 분할된 경우 merge_outputs()를 호출하여 최종 MD, HTML, Items 병합 작업을 수행합니다.
    
    results = preprocess_pdf(pdf_file_path)
    


    # 나중에 주석 풀기
    # 이미지에 캡션 다는것
    generate_captions(OPENAI_API_KEY, BASE_FOLDER) 
    merge_captions_into_md(BASE_FOLDER)
    
    # 오류가 없었다면 저장된 파일의 폴더경로를 반환함
    return BASE_FOLDER
    

if __name__ == "__main__":
    pdf_file_path = "pdf/모니터1p.pdf"
    upstage_document_parse(pdf_file_path)
    