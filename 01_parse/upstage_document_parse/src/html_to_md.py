import os
import re
import sys
import json
from bs4 import BeautifulSoup
from parse_html_table_to_md import parse_html_table_to_md

sys.dont_write_bytecode = True

def convert_to_relative_path(img_abs_path, reference_file_path):
    base_dir = os.path.dirname(reference_file_path)
    rel_path = os.path.relpath(img_abs_path, start=base_dir)
    rel_path = rel_path.replace("\\", "/")
    return f"./{rel_path}"

def build_id_image_map(images_paths):
    """
    이미지 파일명 예: 7_page_1_chart_1.png
    -> 맨 앞 숫자(7)가 elements id
    """
    pattern = re.compile(r'^(\d+)_page_\d+_\w+_\d+\.png$')
    id_map = {}
    for img_path in images_paths:
        fname = os.path.basename(img_path)
        match = pattern.match(fname)
        if match:
            elem_id = match.group(1)
            id_map[elem_id] = img_path
    return id_map

def get_page_info(element):
    """요소의 data-page 속성이 있다면 [Page: X] 문자열을 반환 (최종 출력에서 제외할 예정)"""
    page = element.get("data-page")
    return f"[Page: {page}]" if page else ""

def load_result_json(html_path):
    """html_path와 동일한 폴더 내에 _result.json 파일이 있으면 로드"""
    base_folder = os.path.dirname(html_path)
    base_filename = os.path.splitext(os.path.basename(html_path))[0]
    result_json_path = os.path.join(base_folder, f"{base_filename}_result.json")
    if os.path.exists(result_json_path):
        with open(result_json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def build_metadata_for_element(result, element, html_path):
    """
    반환: {
      "file_name": <파일명>,
      "file_type": <확장자>,
      "html_path": <HTML 파일 경로>,
      "page": <data-page 값>,
      "elementId": <요소의 id>
    }
    """
    metadata = {
        "file_name": os.path.basename(html_path),
        "file_type": os.path.splitext(html_path)[1],
        "html_path": html_path,
        "page": element.get("data-page", ""),
        "elementId": element.get("id", "")
    }
    return metadata

def process_element_block(element, content, html_path, result):
    """
    해당 요소(content와 함께)를 하나의 블록으로 생성합니다.
    MD 파일에는 최소한의 메타데이터로 elementId만 포함하고,
    elementId가 블록의 최상단에 오고 그 아래에 내용이 오도록 합니다.
    블록 구분자는 블록 사이에 한 줄씩만 추가합니다.
    
    예시 출력:
      <<BLOCKEND>>
      elementId: 3
      (내용)
      <<BLOCKEND>>
    """
    # 최소한의 메타데이터: elementId만 추가
    elem_id = element.get("id", "")
    minimal_meta = f"elementId: {elem_id}" if elem_id else ""
    
    block_lines = []
    if minimal_meta:
        block_lines.append(minimal_meta)
    if content:
        block_lines.append(content)
    # 블록 구분자는 각 블록의 끝에 단 한 번만 추가
    block = "\n".join(block_lines) + "\n<<BLOCKEND>>"
    return block

def html_to_md(html_path, images_paths, result=None):
    """
    HTML 파일을 MD 파일로 변환합니다.
    각 최상위 HTML 요소에서 텍스트나 이미지 내용을 추출하고,
    해당 요소의 data-page와 id를 최소한의 메타데이터 (elementId)로 결합하여 블록으로 만듭니다.
    최종 MD 파일은 각 블록이 한 줄의 <<BLOCKEND>>로 구분되며, 
    원래의 전체 메타데이터는 별도의 JSON 파일({파일명}_metadata.json)로 저장됩니다.
    """
    if not os.path.exists(html_path):
        print(f"❌ HTML 파일을 찾을 수 없습니다: {html_path}")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")
    body = soup.body if soup.body else soup

    id_map = build_id_image_map(images_paths)
    blocks = []
    metadata_all = {}  # 전체 메타데이터 저장 (key: elementId)

    def get_text_content(element):
        text = element.get_text(separator="\n")
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        return text.strip()

    # 각 최상위 요소 처리
    for elem in body.find_all(recursive=False):
        # 원래의 전체 메타데이터 생성 및 저장
        metadata = build_metadata_for_element(result if result else {}, elem, html_path)
        element_id = metadata.get("elementId")
        if element_id:
            metadata_all[element_id] = metadata

        tagname = elem.name.lower()
        content = ""
        if tagname in ["p", "header", "h1", "h2", "h3", "h4", "h5", "h6"]:
            content = get_text_content(elem)
            block = process_element_block(elem, content, html_path, result)
            blocks.append(block)
        elif tagname == "br":
            continue
        elif tagname == "table":
            md_table = parse_html_table_to_md(elem)
            lines = md_table.split("\n")
            if len(lines) >= 2:
                col_count = lines[0].count("|") - 1
                sep_line = "| " + " | ".join(["---"] * col_count) + " |"
                lines.insert(1, sep_line)
            content = "\n".join(lines).strip()
            block = process_element_block(elem, content, html_path, result)
            blocks.append(block)
            caption = elem.find("caption")
            if caption:
                cap_text = caption.get_text(strip=True)
                if cap_text:
                    blocks[-1] = blocks[-1].replace("<<BLOCKEND>>", f"**{cap_text}**\n<<BLOCKEND>>", 1)
            elem_id = elem.get("id")
            if elem_id and elem_id in id_map:
                rel_path = convert_to_relative_path(id_map[elem_id], html_path)
                blocks[-1] = blocks[-1].replace("<<BLOCKEND>>", f"![id_{elem_id}]({rel_path})\n<<BLOCKEND>>", 1)
        elif tagname == "img":
            src = elem.get("src", "")
            if not src:
                elem_id = elem.get("id", "")
                if elem_id and elem_id in id_map:
                    src = id_map[elem_id]
            rel_path = convert_to_relative_path(src, html_path) if src else ""
            content = f"![]({rel_path})"
            alt_text = elem.get("alt", "")
            if alt_text:
                content += "\n" + f"*{alt_text}*"
            block = process_element_block(elem, content, html_path, result)
            blocks.append(block)
        elif tagname == "figure":
            block_content = ""
            img = elem.find("img")
            if img:
                src = img.get("src", "")
                if not src:
                    figure_id = elem.get("id", "")
                    if figure_id and figure_id in id_map:
                        src = id_map[figure_id]
                rel_path = convert_to_relative_path(src, html_path) if src else ""
                block_content += f"![]({rel_path})"
                alt_text = img.get("alt", "")
                if alt_text:
                    block_content += "\n" + f"*{alt_text}*"
            else:
                figure_id = elem.get("id", "")
                if figure_id and figure_id in id_map:
                    rel_path = convert_to_relative_path(id_map[figure_id], html_path)
                    block_content += f"![]({rel_path})"
            figcaption = elem.find("figcaption")
            if figcaption:
                caption = get_text_content(figcaption)
                block_content += "\n" + "#### " + caption
            table = elem.find("table")
            if table:
                md_table = parse_html_table_to_md(table)
                lines = md_table.split("\n")
                if len(lines) >= 2:
                    col_count = lines[0].count("|") - 1
                    sep_line = "| " + " | ".join(["---"] * col_count) + " |"
                    lines.insert(1, sep_line)
                md_table_fixed = "\n".join(lines).strip()
                if md_table_fixed:
                    block_content += "\n" + md_table_fixed
            block = process_element_block(elem, block_content, html_path, result)
            blocks.append(block)
        else:
            content = get_text_content(elem)
            block = process_element_block(elem, content, html_path, result)
            blocks.append(block)

    # 최종 MD 파일 생성: 각 블록을 한 줄의 <<BLOCKEND>>로 구분하여 연결
    final_md = "\n".join(blocks)
    out_md_path = html_path.replace(".html", "_converted.md")
    with open(out_md_path, "w", encoding="utf-8") as f:
        f.write(final_md)

    print(f"║ ✅ HTML -> MD 변환 하며 이미지파일명을 추가했습니다:\n║    --> {out_md_path}")

    # 별도의 metadata JSON 파일 생성: {파일명}_metadata.json (키는 elementId)
    base_filename = os.path.splitext(os.path.basename(html_path))[0]
    metadata_json_path = os.path.join(os.path.dirname(html_path), f"{base_filename}_metadata.json")
    with open(metadata_json_path, "w", encoding="utf-8") as f:
        json.dump(metadata_all, f, indent=2, ensure_ascii=False)
    print(f"║ ✅ Metadata JSON 저장 완료: {metadata_json_path}\n║")

    return out_md_path

if __name__ == "__main__":
    # 예시: 인자로 HTML 파일, 이미지 경로 리스트, 그리고 result JSON 전달
    html_to_md("path/to/your_file.html", ["path/to/image1.png", "path/to/image2.png"], result={})
