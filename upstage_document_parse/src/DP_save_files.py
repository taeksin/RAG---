# DP_save_files.py
import os
import sys
from datetime import datetime
from PDFImageExtractor import PDFImageExtractor 

sys.dont_write_bytecode = True

# Document Parse의 결과를 저장할 폴더 설정
TEMP_DIR = "upstage_document_parse/temp"
os.makedirs(TEMP_DIR, exist_ok=True)  # temp 폴더가 없으면 생성

def save_files(result, filename):
    """
    API 응답 데이터를 받아서 HTML, TXT, Markdown 파일로 저장하고,
    PDF에서 chart/table/figure 요소에 해당하는 영역을 크롭하여 이미지로 저장한다.
    그리고 (file_paths, images_paths)를 반환한다.
    """
    date_str = datetime.now().strftime("%y%m%d-%H-%M")
    content = result.get("content", {})
    elements = result.get("elements", [])

    # base_filename, base_folder 설정
    base_filename = "[DP]_" + date_str + "_" + os.path.splitext(os.path.basename(filename))[0]
    base_folder = os.path.join(TEMP_DIR, base_filename)
    os.makedirs(base_folder, exist_ok=True)

    file_paths = {}    # HTML/MD/TXT 파일 경로들
    images_paths = []  # 크롭된 이미지 경로들

    # 1) HTML 저장
    if "html" in content and content["html"]:
        html_path = os.path.join(base_folder, f"{base_filename}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(content["html"])
        file_paths["html"] = html_path
        print(f"✅ HTML 저장 완료: {html_path}")
    else:
        print("⚠️ HTML 데이터가 비어 있습니다.")

    # # 2) TXT 저장
    # if "text" in content and content["text"]:
    #     txt_path = os.path.join(base_folder, f"{base_filename}.txt")
    #     with open(txt_path, "w", encoding="utf-8") as f:
    #         f.write(content["text"])
    #     file_paths["txt"] = txt_path
    #     print(f"✅ TXT 저장 완료: {txt_path}")
    # else:
    #     print("⚠️ TXT 데이터가 비어 있습니다.")

    # # 3) Markdown 저장
    # if "markdown" in content and content["markdown"]:
    #     md_path = os.path.join(base_folder, f"{base_filename}.md")
    #     with open(md_path, "w", encoding="utf-8") as f:
    #         f.write(content["markdown"])
    #     file_paths["md"] = md_path
    #     print(f"✅ Markdown 저장 완료: {md_path}")
    # else:
    #     print("⚠️ Markdown 데이터가 비어 있습니다.")

    # 4) PDF 이미지 크롭
    if elements:
        crop_folder = os.path.join(base_folder, "Items")
        os.makedirs(crop_folder, exist_ok=True)
                
        extractor = PDFImageExtractor(filename, dpi=300)
        images_paths = extractor.extract_elements(elements, crop_folder)  # 리스트 형태로 반환

        # print(f"✅ 이미지 크롭 완료! 총 {len(images_paths)}개 파일.")
    else:
        print("⚠️ API 응답에 elements 정보가 없습니다.")

    print("🎉 모든 파일 저장 및 이미지 크롭이 완료되었습니다!")

    # **file_paths (HTML/MD/TXT)와 images_paths (크롭된 이미지 경로) 리턴**
    return file_paths, images_paths
