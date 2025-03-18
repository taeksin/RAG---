# main.py
import os
import sys
# from 01_pre_processing.upstage_document_parse.src.upstage_document_parser import upstage_document_parse
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
UPSTAGE_SRC_DIR = os.path.join(CURRENT_DIR, "01_pre_processing", "upstage_document_parse", "src")
# Python이 모듈 검색 시 UPSTAGE_SRC_DIR을 찾도록 path 추가
if UPSTAGE_SRC_DIR not in sys.path:
    sys.path.append(UPSTAGE_SRC_DIR)

from upstage_document_parser import upstage_document_parse  # 예: 함수명이 upstage_document_parse라고 가정

print(f"CURRENT_DIR: {CURRENT_DIR}")

# 이제 upstage_document_parser.py 안에 있는 함수를 import

def main():
    # 사용자가 원하는 PDF 파일 경로
    pdf_file_path = "pdf/모니터1~2p.pdf"
    # upstage_document_parse 함수에 파일 경로 전달
    upstage_document_parse(pdf_file_path)

if __name__ == "__main__":
    main()
