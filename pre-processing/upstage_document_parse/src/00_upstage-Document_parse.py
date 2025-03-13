# 00_upstage-Document_parse.py
import os
import sys
import fitz
import time
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
    PDF 파일을 Upstage Document Parse API를 사용하여 분석하고 결과를 temp 폴더에 저장한 뒤,
    그 HTML 파일을 MD로 변환하고, base_folder를 전역 변수에 저장합니다.
    """
    global BASE_FOLDER
    url = "https://api.upstage.ai/v1/document-ai/document-parse"
    headers = {"Authorization": f"Bearer {UPSTAGE_API_KEY}"}
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
        result = response.json()
        file_paths, images_paths, base_folder = save_files(result, filename)
        BASE_FOLDER = base_folder.replace("\\", "/")
        html_path = file_paths.get("html")
        if html_path:
            new_md_path = html_to_md(html_path, images_paths)
        end_time = time.time()
        print(f"⏱️_파싱 소요시간: {end_time - start_time:.2f}초\n")
        return file_paths, images_paths, base_folder
    else:
        error_msg = f"❌ API 요청 실패: {response.status_code}, {response.text}"
        print(error_msg)
        return {}, []

def process_pdf_with_split(pdf_path, split_threshold=100, batch_size=50):
    """
    PDF 페이지 수가 split_threshold 이상이면 batch_size 단위로 분할하여 각각 파싱하고,
    결과와 분할된 PDF 파일 리스트를 반환합니다.
    
    분할된 파일들이 많을 경우, 현재 컴퓨터의 CPU 코어 수의 절반까지 비동기로 실행합니다.
    """
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    if total_pages > split_threshold:
        print(f"PDF 페이지 수({total_pages})가 {split_threshold}를 초과하여, {batch_size}페이지씩 분할합니다.")
        split_files = split_pdf(pdf_path, batch_size=batch_size)
        results = []
        max_workers = max(1, os.cpu_count() // 2)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(preprocess_pdf, split_file): split_file for split_file in split_files}
            for future in concurrent.futures.as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    print(f"{file} 처리 중 예외 발생: {exc}")
        return results, split_files
    else:
        print(f"PDF 페이지 수({total_pages})가 {split_threshold} 이하이므로 단일 파일로 파싱합니다.")
        return [preprocess_pdf(pdf_path)], []

if __name__ == "__main__":
    # 사용 예시: PDF 파일이 100페이지 이상이면 분할 후 각각 파싱하고,
    # 분할된 경우 merge_outputs()를 호출하여 최종 MD, HTML, Items 병합 작업을 수행합니다.
    pdf_file = "pdf/모니터6~7p.pdf"
    results, split_files = process_pdf_with_split(pdf_file, split_threshold=100, batch_size=50)
    
    if split_files:
        merged_md_path, merged_html_path, merged_items_folder = merge_outputs(results, split_files, pdf_file)
        print("최종 병합 결과:")
        print("MD:", merged_md_path)
        print("HTML:", merged_html_path)
        print("Items 폴더:", merged_items_folder)

    # 나중에 주석 풀기
    # 이미지에 캡션 다는것
    generate_captions(OPENAI_API_KEY, BASE_FOLDER) 
    merge_captions_into_md(BASE_FOLDER)