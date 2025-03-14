# merge_outputs.py
import os
import shutil
from datetime import datetime

def merge_outputs(results, split_files, original_pdf_path):
    """
    분할된 결과(results)에서 각 조각의 HTML 파일, MD 파일(HTML 파일 기반 "_converted.md"),
    그리고 Items 폴더를 페이지 순서대로 병합합니다.
    
    병합 후에는 분할 PDF 파일과 개별 조각 결과 폴더(HTML, MD, Items 폴더)를 삭제합니다.
    
    인자:
      results: 각 분할 PDF 조각에 대해 (file_paths, images_paths)를 담은 리스트.
               file_paths는 'html' 키로 HTML 파일 경로를 포함합니다.
      split_files: 분할된 PDF 파일들의 경로 리스트.
      original_pdf_path: 원본 PDF 파일 경로.
    
    반환:
      병합된 MD 파일, HTML 파일, Items 폴더의 경로를 튜플로 반환합니다.
    """
    # 각 결과에서 HTML 파일 경로를 기준으로 시작 페이지를 추출하여 정렬합니다.
    merged_items = []  # (start_page, file_paths) 튜플 목록
    for res in results:
        file_paths, _ = res
        html_path = file_paths.get("html")
        if html_path:
            # 예시 파일명: YYYYMMDD_..._1~50.html
            base = os.path.basename(html_path)
            parts = base.rsplit("_", 1)
            if len(parts) == 2:
                page_range_part = parts[1].split(".")[0]  # 예: "1~50"
                try:
                    start_page = int(page_range_part.split("~")[0])
                except Exception:
                    start_page = 0
            else:
                start_page = 0
            merged_items.append((start_page, file_paths))
    merged_items.sort(key=lambda x: x[0])
    
    # 병합 결과물을 저장할 폴더 생성 (원본 PDF의 base name 사용)
    TEMP_DIR = os.path.join("01_pre-processing", "upstage_document_parse", "temp")
    original_basename = os.path.splitext(os.path.basename(original_pdf_path))[0]
    timestamp = datetime.now().strftime("%y%m%d-%H-%M")
    merged_folder = os.path.join(TEMP_DIR, f"{timestamp}_{original_basename}")
    os.makedirs(merged_folder, exist_ok=True)
    
    # MD 파일 병합: 각 조각의 MD 파일은 HTML 파일 이름에서 ".html"을 "_converted.md"로 대체하여 생성됨
    merged_md_content = ""
    for start_page, file_paths in merged_items:
        html_path = file_paths.get("html")
        if html_path:
            md_path = html_path.replace(".html", "_converted.md")
            if os.path.exists(md_path):
                with open(md_path, "r", encoding="utf-8") as f:
                    merged_md_content += f.read() + "\n\n"
    merged_md_path = os.path.join(merged_folder, f"{original_basename}_converted.md")
    with open(merged_md_path, "w", encoding="utf-8") as f:
        f.write(merged_md_content)
    
    # HTML 파일 병합: 각 조각의 HTML 파일 내용을 단순히 이어 붙입니다.
    merged_html_content = ""
    for start_page, file_paths in merged_items:
        html_path = file_paths.get("html")
        if html_path and os.path.exists(html_path):
            with open(html_path, "r", encoding="utf-8") as f:
                merged_html_content += f.read() + "\n\n"
    merged_html_path = os.path.join(merged_folder, f"{original_basename}.html")
    with open(merged_html_path, "w", encoding="utf-8") as f:
        f.write(merged_html_content)
    
    # Items 폴더 병합: 각 조각의 결과 폴더 내 "Items" 폴더의 모든 파일을 하나의 폴더로 복사합니다.
    merged_items_folder = os.path.join(merged_folder, "Items")
    os.makedirs(merged_items_folder, exist_ok=True)
    for start_page, file_paths in merged_items:
        html_path = file_paths.get("html")
        if html_path:
            result_folder = os.path.dirname(html_path)
            items_folder = os.path.join(result_folder, "Items")
            if os.path.exists(items_folder):
                for filename in os.listdir(items_folder):
                    src = os.path.join(items_folder, filename)
                    dst = os.path.join(merged_items_folder, filename)
                    shutil.copy(src, dst)
    
    # 중간 결과 폴더 삭제: 각 조각의 결과 폴더(HTML, MD, Items 포함)를 삭제합니다.
    folders_to_delete = set()
    for start_page, file_paths in merged_items:
        html_path = file_paths.get("html")
        if html_path:
            folders_to_delete.add(os.path.dirname(html_path))
    for folder in folders_to_delete:
        shutil.rmtree(folder)
    
    # 분할된 PDF 파일 삭제
    for split_file in split_files:
        if os.path.exists(split_file):
            os.remove(split_file)
    
    print("✅ 병합 완료:")
    print("   병합된 MD 파일:", merged_md_path)
    print("   병합된 HTML 파일:", merged_html_path)
    print("   병합된 Items 폴더:", merged_items_folder)
    return merged_md_path, merged_html_path, merged_items_folder

# if __name__ == "__main__":
#     # 테스트용 예시 (실제 사용 시 process_pdf_with_split() 등에서 인자로 전달)
#     # 예시:
#     # results = [
#     #    ({"html": "01_pre-processing/upstage_document_parse/temp/[DP]_20241220_..._1~50.html"}, []),
#     #    ({"html": "01_pre-processing/upstage_document_parse/temp/[DP]_20241220_..._51~100.html"}, [])
#     # ]
#     # split_files = ["pdf/sample_1~50.pdf", "pdf/sample_51~100.pdf"]
#     # merge_outputs(results, split_files, "pdf/sample.pdf")
#     pass
