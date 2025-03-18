# main.py
import os
import sys
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
    pdf_file_path = "pdf/모니터1p.pdf"
    result_folder = upstage_document_parse(pdf_file_path)
    print("저장된 폴더 경로:", result_folder)

    # result_folder 내에 _merged.md로 끝나는 파일을 찾아 file_path로 할당
    file_path = None
    for filename in os.listdir(result_folder):
        if filename.endswith("_merged.md"):
            file_path = os.path.join(result_folder, filename)
            break

    if not file_path:
        print("'_merged.md' 파일을 찾을 수 없습니다.")
        return
    
    # split 시작 1~4 방법으로 수행 후, 각 함수의 반환값을 리스트로 모음
    p1 = process_file_01(file_path).replace("\\", "/")
    p2 = process_file_02(file_path).replace("\\", "/")
    p3 = process_file_03(file_path).replace("\\", "/")
    p4 = process_file_04(file_path).replace("\\", "/")
    
    md_file_paths = [p1, p2, p3, p4]
    print(f"\n[SPLIT 완료] 총: {len(md_file_paths)}개\n")
    
    # 병렬 실행을 위해 ThreadPoolExecutor 사용
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # embedding_md_to_faiss 함수를 병렬로 실행
        future_to_path = {executor.submit(embedding_md_to_faiss, path): path for path in md_file_paths}
        
        for future in concurrent.futures.as_completed(future_to_path):
            md_path = future_to_path[future]
            try:
                result = future.result()
                results.append((md_path, result))
            except Exception as e:
                print(f"[오류 발생] 파일: {md_path}, 오류: {e}")

if __name__ == "__main__":
    main()
