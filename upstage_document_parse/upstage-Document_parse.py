# upstage-Document_parse.py
import os
import requests
import time
from dotenv import load_dotenv
from datetime import datetime
from DP_save_files import save_files  
from make_html_to_md import make_html_to_md 

load_dotenv()
API_KEY = os.getenv("API_KEY")

if not API_KEY:
    raise ValueError("API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

def preprocess_pdf(filename):
    """
    PDF 파일을 Upstage Document Parse API를 사용하여 분석하고 결과를 temp 폴더에 저장한 뒤,
    그 HTML 파일을 MD로 변환.
    """
    url = "https://api.upstage.ai/v1/document-ai/document-parse"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    start_time = time.time()

    with open(filename, "rb") as f:
        files = {"document": f}
        data = {
            "output_formats": "['html', 'text', 'markdown']",
            "ocr": "force",
            "base64_encoding": "['table']",
            "model": "document-parse"
        }

        print(f"📤 PDF 파일 {filename} 을(를) API에 업로드 중...")
        response = requests.post(url, headers=headers, files=files, data=data)

    if response.status_code == 200:
        print("📥 API 응답 데이터 수신 완료!")
        result = response.json()

        # 1) 파일 저장 (HTML, MD, TXT + 이미지 크롭)
        file_paths, images_paths = save_files(result, filename)

        # 2) HTML -> Markdown 변환 (우리가 만든 make_html_to_md 호출)
        html_path = file_paths.get("html")
        if html_path:
            # 변환 실행
            new_md_path = make_html_to_md(html_path, images_paths)
            print(f"📝 새롭게 변환된 MD: {new_md_path}")

        end_time = time.time()
        print(f"⏱️ 총 실행 시간: {end_time - start_time:.2f}초")

        return file_paths, images_paths
    else:
        error_msg = f"❌ API 요청 실패: {response.status_code}, {response.text}"
        print(error_msg)
        return {}, []

if __name__ == "__main__":
    pdf_file = "pdf/[꿈꾸는라이언]1-6.pdf"
    file_paths, images_paths = preprocess_pdf(pdf_file)
