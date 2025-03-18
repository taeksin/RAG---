import os
import sys
import fitz
import concurrent.futures

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
UPSTAGE_SRC_DIR = os.path.join(CURRENT_DIR, "01_pre_processing", "upstage_document_parse", "src")
SPLIT_DIR = os.path.join(CURRENT_DIR, "02_split")
EMBEDDING_DIR = os.path.join(CURRENT_DIR, "03_embedding")

for path in [UPSTAGE_SRC_DIR, SPLIT_DIR, EMBEDDING_DIR]:
    if path not in sys.path:
        sys.path.append(path)

from upstage_document_parser import upstage_document_parse
from split_01 import process_file_01
from split_02 import process_file_02
from split_03 import process_file_03
from split_04 import process_file_04
from upstage_md_to_faiss import embedding_md_to_faiss

def main():
    # 로컬 함수: 단일 PDF 처리 (process_one_pdf의 내용을 main 내부로 인라인)
    def process_pdf(pdf_file_path):
        # 1) PDF 파싱: upstage_document_parse를 호출하여 저장된 폴더 경로 획득
        result_folder = upstage_document_parse(pdf_file_path)
        print(f"[PDF 파싱 완료] {pdf_file_path} -> 저장된 폴더: {result_folder}")

        # 2) 저장된 폴더 내에서 '_merged.md' 파일 찾기
        file_path = None
        for filename in os.listdir(result_folder):
            if filename.endswith("_merged.md"):
                file_path = os.path.join(result_folder, filename)
                break

        if not file_path:
            err_msg = f"'_merged.md' 파일을 찾을 수 없습니다. (폴더: {result_folder})"
            print(err_msg)
            return {"pdf": pdf_file_path, "error": err_msg}

        # 3) split 4가지 방법 수행하여 4개의 MD 파일 경로 생성
        p1 = process_file_01(file_path).replace("\\", "/")
        p2 = process_file_02(file_path).replace("\\", "/")
        p3 = process_file_03(file_path).replace("\\", "/")
        p4 = process_file_04(file_path).replace("\\", "/")
        md_file_paths = [p1, p2, p3, p4]
        print(f"[SPLIT 완료] {pdf_file_path}")

        # 4) 각 MD 파일에 대해 임베딩 수행 (embedding_md_to_faiss)
        embed_results = []
        for md_path in md_file_paths:
            try:
                res = embedding_md_to_faiss(md_path)
                embed_results.append((md_path, res))
            except Exception as e:
                print(f"[오류 발생] MD: {md_path}, 오류: {e}")

        # 최종 결과 반환
        return {
            "pdf_file": pdf_file_path,
            "split_md_paths": md_file_paths,
            "embed_results": embed_results,
        }

    # PDF 폴더와 파일명 설정 (PDF 폴더는 한 번만 지정)
    pdf_folder = "pdf"
    pdf_filenames = [
        "모니터1p.pdf",
        "모니터1~2p.pdf",
        # 필요시 추가...
    ]
    pdf_file_paths = [os.path.join(pdf_folder, fname) for fname in pdf_filenames]

    # 병렬 실행: 사용 가능한 CPU 코어의 절반만큼의 스레드 사용
    max_workers = max(1, os.cpu_count() // 2)
    print(f"[INFO] 병렬 실행(스레드) 수: {max_workers}")
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pdf = {executor.submit(process_pdf, pdf): pdf for pdf in pdf_file_paths}
        for future in concurrent.futures.as_completed(future_to_pdf):
            pdf_path = future_to_pdf[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"[오류 발생] PDF: {pdf_path}, 오류: {e}")

    print("\n-------------------------------------")
    print(f"[총 {len(pdf_filenames)}개 파일 파싱부터 임베딩까지 모두 끝났습니다.]")
    print("-------------------------------------\n")

    # -------------------------------
    # 전체 사용한 PDF 파일의 페이지 수 합산
    # -------------------------------
    total_pages = 0
    for pdf_path in pdf_file_paths:
        with fitz.open(pdf_path) as doc:
            total_pages += len(doc)
    print("-------------------------------------")
    print(f"[최종] 사용한 전체 PDF의 페이지수: {total_pages}")
    print("-------------------------------------")

if __name__ == "__main__":
    main()
