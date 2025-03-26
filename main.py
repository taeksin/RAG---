import os
import sys
import fitz

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
UPSTAGE_SRC_DIR = os.path.join(CURRENT_DIR, "01_parse", "upstage_document_parse", "src")
SPLIT_DIR = os.path.join(CURRENT_DIR, "02_split")
EMBEDDING_DIR = os.path.join(CURRENT_DIR, "03_embedding")

for path in [UPSTAGE_SRC_DIR, SPLIT_DIR, EMBEDDING_DIR]:
    if path not in sys.path:
        sys.path.append(path)

from upstage_document_parser import upstage_document_parse
from split_pdf import split_pdf
from split_01 import process_file_01
from split_02 import process_file_02
from split_03 import process_file_03
from split_04 import process_file_04
from excel_save import save_md_to_excel
from excel_embedding import embedding_xl_to_faiss

# 전역으로 4개의 Excel 파일 경로를 지정 (p1, p2, p3, p4 결과를 각각 저장)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

excel_file_paths = [
    os.path.join(DATA_DIR, "all_01.xlsx"),
    os.path.join(DATA_DIR, "all_02.xlsx"),
    os.path.join(DATA_DIR, "all_03.xlsx"),
    os.path.join(DATA_DIR, "all_04.xlsx")
]


def process_pdf(pdf_file_path, pdf_index, total_pdfs):
    # pdf_index에 따라 indicator 결정
    if pdf_index == 0:
        indicator = "first"
    elif pdf_index == total_pdfs - 1:
        indicator = "final"
    else:
        indicator = str(pdf_index + 1)
    
    # 1) PDF 파싱: PDF를 읽어 저장된 폴더 경로 획득
    result_folder = upstage_document_parse(pdf_file_path)
    print(f"║ 🟢[PDF 파싱 완료] {pdf_file_path} -> 저장된 폴더: {result_folder}")

    # 2) 저장된 폴더 내에서 '_merged.md' 파일 찾기
    merged_md = None
    for filename in os.listdir(result_folder):
        if filename.endswith("_merged.md"):
            merged_md = os.path.join(result_folder, filename)
            break
    if not merged_md:
        err_msg = f"'_merged.md' 파일을 찾을 수 없습니다. (폴더: {result_folder})"
        print(err_msg)
        return

    # 3) split 4가지 방법 수행하여 4개의 MD 파일 경로 생성
    p1 = process_file_01(merged_md).replace("\\", "/")
    p2 = process_file_02(merged_md).replace("\\", "/")
    p3 = process_file_03(merged_md).replace("\\", "/")
    p4 = process_file_04(merged_md).replace("\\", "/")
    md_file_paths = [p1, p2, p3, p4]
    print(f"║ 🟢[SPLIT 완료] {pdf_file_path} \n║")
    print("╚════════════════════════════════════════")
    

    # 4) 각 MD 파일에 대해 해당 Excel 파일에 저장 (인덱스별로 분리)
    for idx, md_path in enumerate(md_file_paths):
        if idx == 0:
            excel_path = excel_file_paths[0]
        elif idx == 1:
            excel_path = excel_file_paths[1]
        elif idx == 2:
            excel_path = excel_file_paths[2]
        elif idx == 3:
            excel_path = excel_file_paths[3]
        else:
            continue
        # indicator는 위에서 pdf의 순서를 기준으로 설정한 값 사용
        try:
            save_md_to_excel(md_path, indicator, excel_path)
        except Exception as e:
            print(f"[오류 발생] MD: {md_path}, 오류: {e}")

def main():
    # PDF 폴더와 파일명 설정
    pdf_folder = "pdf"
    pdf_filenames = [
        "9.pdf",
        # "[보조교재]_연말정산 세무_이석정_한국_회원_3.5시간.pdf",
        # "차트2_표1.pdf",
        # "모니터1p.pdf",
    ]
    # 원본 PDF 파일 경로 리스트 생성
    original_pdf_paths = [os.path.join(pdf_folder, fname) for fname in pdf_filenames]
    
    # 모든 PDF 파일을 하나씩 split_pdf 함수에 넣어 처리한 후,
    # 각 파일에 대해 반환된 결과(리스트)를 모두 합쳐 new_pdf_file_paths에 저장
    pdf_file_paths = []
    for path in original_pdf_paths:
        result = split_pdf(path)
        # split_pdf()는 항상 리스트를 반환함 (분할되지 않으면 [path] 반환)
        pdf_file_paths.extend(result)
    
    total_pdfs = len(pdf_file_paths)

    # 순차적으로 각 PDF 처리
    for idx, pdf_path in enumerate(pdf_file_paths):
        process_pdf(pdf_path, idx, total_pdfs)

    # 임베딩
    print("╔════════════════════════════════════════")
    embedding_xl_to_faiss(excel_file_paths)
    print("╚════════════════════════════════════════")
    
    print("\n-------------------------------------")
    print(f"[총 {len(pdf_filenames)}개 PDF 파일 처리 완료]")

    # 전체 사용한 PDF 파일의 페이지 수 합산 (확인용)
    total_pages = 0
    for pdf_path in pdf_file_paths:
        with fitz.open(pdf_path) as doc:
            total_pages += len(doc)
    print("-------------------------------------")
    print(f"[최종] 사용한 전체 PDF의 페이지수: {total_pages}")
    print("-------------------------------------")

if __name__ == "__main__":
    main()
