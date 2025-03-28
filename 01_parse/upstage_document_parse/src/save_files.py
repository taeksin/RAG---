import os
import sys
import glob
import json
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup  # HTML 수정용
from PDFImageExtractor import PDFImageExtractor 
sys.dont_write_bytecode = True

# Document Parse의 결과를 저장할 폴더 설정
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)  # data 폴더가 없으면 생성

def save_files(result, filename):
    """
    API 응답 데이터를 받아서 HTML, TXT, Markdown 파일로 저장하고,
    PDF에서 chart/table/figure 요소에 해당하는 영역을 크롭하여 이미지로 저장한다.
    또한 API 결과(result) 전체도 JSON 파일로 저장한다.
    그리고 (file_paths, images_paths)를 반환한다.
    """
    date_str = datetime.now().strftime("%y%m%d-%H-%M")
    content = result.get("content", {})
    elements = result.get("elements", [])

    # base_filename, base_folder 설정
    base_filename = date_str + "_" + os.path.splitext(os.path.basename(filename))[0]
    base_folder = os.path.join(DATA_DIR, base_filename)
    os.makedirs(base_folder, exist_ok=True)

    file_paths = {}    # HTML/MD/TXT 파일 경로들
    images_paths = []  # 크롭된 이미지 경로들
    
    print("║ ✅ upstage의 결과를 저장합니다.")
    
    # 1) TXT 저장
    if "text" in content and content["text"]:
        txt_path = os.path.join(base_folder, f"{base_filename}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(content["text"])
        file_paths["txt"] = txt_path
        print(f"║   -> TXT 저장 완료: {txt_path}")
    else:
        print("⚠️ TXT 데이터가 비어 있습니다.")

    # 2) Markdown 저장
    if "markdown" in content and content["markdown"]:
        md_path = os.path.join(base_folder, f"{base_filename}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content["markdown"])
        file_paths["md"] = md_path
        print(f"║   -> Markdown 저장 완료: {md_path}")
    else:
        print("⚠️ Markdown 데이터가 비어 있습니다.")

    # 3) API 결과(result) 전체를 JSON 파일로 저장
    result_path = os.path.join(base_folder, f"{base_filename}_result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    file_paths["result"] = result_path
    print(f"║   -> API 결과 저장 완료: {result_path}\n║")

    # 4) PDF 이미지 크롭
    if elements:
        crop_folder = os.path.join(base_folder, "Items")
        os.makedirs(crop_folder, exist_ok=True)
                
        extractor = PDFImageExtractor(filename, dpi=300)
        images_paths = extractor.extract_elements(elements, crop_folder)  # 리스트 형태로 반환
        print(f"║   -> 이미지 크롭 완료! 총 {len(images_paths)}개.")
    else:
        print("⚠️ API 응답에 elements 정보가 없습니다.")

    # 5) HTML 저장 (수정: elements의 "page" 정보를 각 태그에 추가 및 alt 속성 업데이트)
    if "html" in content and content["html"]:
        html_str = sort_html_by_id(content["html"])
        soup = BeautifulSoup(html_str, "html.parser")
        # elements에 있는 각 요소에 대해, id가 일치하는 태그에 data-page 속성 추가
        for elem in elements:
            elem_id = str(elem.get("id", ""))
            page = elem.get("page")
            if elem_id and page is not None:
                tag = soup.find(attrs={"id": elem_id})
                if tag:
                    tag["data-page"] = str(page)
        # images_paths 리스트에서 파일명을 이용해 alt 속성 매핑 생성
        # 파일명 예: "3_page_1_table_1.png" -> element id: "3", 페이지: "1"
        alt_mapping = {}
        for img_path in images_paths:
            fname = os.path.basename(img_path)
            parts = fname.split("_")
            if len(parts) >= 3:
                elem_id = parts[0]
                page_num = parts[2]  # 사용 예: 페이지 번호 (필요에 따라 활용 가능)
                # alt 정보로 파일명을 사용 (여러 이미지가 같은 element id에 해당하면 콤마로 연결)
                if elem_id in alt_mapping:
                    alt_mapping[elem_id] += ", " + fname
                else:
                    alt_mapping[elem_id] = fname

        # 매핑된 정보를 바탕으로 해당 태그의 alt 속성 업데이트
        for elem_id, alt_text in alt_mapping.items():
            tag = soup.find(attrs={"id": elem_id})
            if tag:
                existing_alt = tag.get("alt", "")
                tag["alt"] = (existing_alt + " " + alt_text).strip() if existing_alt else alt_text

        modified_html = str(soup)
        
        html_path = os.path.join(base_folder, f"{base_filename}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(modified_html)
        file_paths["html"] = html_path
        print(f"║   -> HTML 저장 완료: {html_path}")
    else:
        print("⚠️ HTML 데이터가 비어 있습니다.")

    html_to_excel(base_folder)
    
    # **file_paths (HTML/MD/TXT, result JSON)와 images_paths (크롭된 이미지 경로) 리턴**
    return file_paths, images_paths, base_folder

def sort_html_by_id(html_str):
    soup = BeautifulSoup(html_str, "html.parser")

    # id가 있는 요소만 추출
    id_elements = soup.find_all(attrs={"id": True})

    # id 기준 정렬 (숫자 우선, 안 되면 문자열)
    def get_id(elem):
        try:
            return int(elem.get("id"))
        except:
            return str(elem.get("id"))

    sorted_elements = sorted(id_elements, key=get_id)

    # 정렬된 요소만 새로운 soup에 추가
    new_soup = BeautifulSoup("", "html.parser")
    for elem in sorted_elements:
        new_soup.append(elem)

    return str(new_soup)


def html_to_excel(base_folder):
    """
    base_folder 내의 .html 파일을 찾아서,
    각 요소에 대해 다음 정보를 엑셀로 저장합니다.
    
    헤더: 파일명 | 페이지숫자 | elementid | data-category | alt(존재할 때만) | 내용
    
    만약 data-category 속성이 없으면 태그 이름을 사용하며,
    파일명은 확장자 없이 저장합니다.
    """
    rows = []
    # base_folder 내의 .html 파일 찾기
    html_files = glob.glob(os.path.join(base_folder, "*.html"))
    if not html_files:
        print("HTML 파일을 찾지 못했습니다.")
        return

    for html_file in html_files:
        # 파일명에서 확장자 제거
        # file_name = "_".join(os.path.splitext(os.path.basename(html_file))[0].split("_")[1:])
        file_name = os.path.splitext(os.path.basename(html_file))[0]
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()
        soup = BeautifulSoup(html_content, "html.parser")
        # id 속성이 있는 모든 태그 대상으로 처리
        elements = soup.find_all(attrs={"id": True})
        for elem in elements:
            page_num = elem.get("data-page", "").strip()
            elem_id = elem.get("id", "").strip()
            # data-category 없으면 태그 이름 사용
            data_category = elem.get("data-category", "").strip() or elem.name
            alt = elem.get("alt", "").strip()
            content = elem.get_text(separator="\n").strip()
            row = {
                "파일명": file_name,
                "페이지숫자": page_num,
                "elementid": elem_id,
                "data-category": data_category,
                "alt": alt,
                "내용": content,
                "이미지설명":""
            }
            rows.append(row)
    if not rows:
        print("추출할 요소가 없습니다.")
        return

    df = pd.DataFrame(rows, columns=["파일명", "페이지숫자", "elementid", "data-category", "alt", "내용", "이미지설명"])
    # 엑셀 파일명은 base_folder의 이름을 사용하여 저장 (예: 모니터8p.xlsx)
    base_name = os.path.basename(os.path.normpath(base_folder))
    excel_path = os.path.join(base_folder, f"{base_name}.xlsx")
    df.to_excel(excel_path, index=False)
    print(f"║   -> 엑셀 파일 생성 완료: {excel_path}")