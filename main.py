import os
import sys
import fitz

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
UPSTAGE_SRC_DIR = os.path.join(CURRENT_DIR, "01_parse", "upstage_document_parse", "src")
CONSTRUCT_DIR = os.path.join(CURRENT_DIR, "02_construct")
EMBEDDING_DIR = os.path.join(CURRENT_DIR, "03_embedding")

for path in [UPSTAGE_SRC_DIR, CONSTRUCT_DIR, EMBEDDING_DIR]:
    if path not in sys.path:
        sys.path.append(path)

from upstage_document_parser import upstage_document_parse
from split_pdf import split_pdf 
from construct_content_metadata import construct_embedding_contents
from openaiEmbedding import openaiEmbedding
from upstageEmbedding import upstageEmbedding

def main():
    pdf_folder = "pdf"
    pdf_filenames = [
        # "[보조교재]_연말정산 세무_이석정_한국_회원_3.5시간.pdf",
        # "차트2_표1.pdf",
        "모니터8p.pdf",
        "모니터1p.pdf",
    ]
    
    # upstage_document_parse의 반환값(폴더 경로)을 담을 리스트
    all_result_folders = []
    
    for filename in pdf_filenames:
        pdf_path = os.path.join(pdf_folder, filename)
        
        # PDF 페이지 수 확인 (선택적)
        with fitz.open(pdf_path) as doc:
            page_count = doc.page_count
        # print(f"처리 중인 PDF: {pdf_path} (총 페이지: {page_count})")
        
        # split_pdf 함수 호출: PDF가 100페이지 미만이면 [원본경로]를, 이상이면 분할된 파일 목록을 반환
        pdf_list = split_pdf(pdf_path)
        
        # 분할된 각 파일에 대해 upstage_document_parse 호출 후 반환값(폴더 경로)를 리스트에 저장
        for file in pdf_list:
            result_folder = upstage_document_parse(file)
            print(f"║ ✅ [PDF 파싱 완료] {file} -> 저장된 폴더: {result_folder}")
            all_result_folders.append(result_folder)
        print("╚════════════════════════════════════════\n")
        
    # 모든 PDF 처리가 끝난 후, 각 결과 폴더에 대해 construct_embedding_contents 실행 후,
    # 반환된 construct_path를 construct_paths 리스트에 저장
    
    # for folder in all_result_folders:
    #     construct_path = construct_embedding_contents(folder)
    #     # 경로 구분자를 replace()로 통일: 백슬래시를 슬래시로 변경
    #     normalized_path = construct_path.replace("\\", "/")
    #     construct_paths.append(normalized_path)
    construct_path = construct_embedding_contents(all_result_folders)
    
    # construct_paths 리스트에 있는 폴더 경로를 사용하여 임베딩 실행
    print("║ ✅ openaiEmbedding 시작")
    openaiEmbedding(construct_path)
    print("║ ✅ upstageEmbedding 시작")
    upstageEmbedding(construct_path)
    print("╚════════════════════════════════════════\n")

if __name__ == "__main__":
    main()
