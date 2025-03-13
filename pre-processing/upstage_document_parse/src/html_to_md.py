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
    메타데이터는 build_metadata_for_element()를 통해 JSON 문자열로 만들어집니다.
    반환 예시:
      <<BLOCKEND>>
      (content)
      metadata:{ ... }
      <<BLOCKEND>>
    """
    metadata = build_metadata_for_element(result if result else {}, element, html_path)
    metadata_str = "metadata:" + json.dumps(metadata, indent=2, ensure_ascii=False)
    block_lines = []
    if content:
        block_lines.append(content)
    block_lines.append(metadata_str)
    block = "<<BLOCKEND>>\n" + "\n".join(block_lines) + "\n<<BLOCKEND>>"
    return block

def html_to_md(html_path, images_paths, result=None):
    """
    HTML 파일을 MD 파일로 변환합니다.
    각 최상위 HTML 요소에서 텍스트나 이미지 내용을 추출하고,
    해당 요소의 data-page와 id를 메타데이터로 결합한 후 하나의 블록으로 만듭니다.
    최종 MD 파일은 연속된 <<BLOCKEND>>와 불필요한 빈 줄이 제거된 상태로 저장됩니다.
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

    def get_text_content(element):
        text = element.get_text(separator="\n")
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        return text.strip()

    # 각 요소별로 처리하여 하나의 블록으로 생성
    for elem in body.find_all(recursive=False):
        tagname = elem.name.lower()
        content = ""
        if tagname in ["p", "header", "h1", "h2", "h3", "h4", "h5", "h6"]:
            content = get_text_content(elem)
            block = process_element_block(elem, content, html_path, result)
            blocks.append(block)
        elif tagname == "br":
            # br 태그는 별도의 블록으로 처리하지 않음
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
                    # 캡션은 별도 블록 없이 기존 블록에 바로 추가
                    blocks[-1] = blocks[-1].replace("<<BLOCKEND>>", f"**{cap_text}**\n<<BLOCKEND>>", 1)
            elem_id = elem.get("id")
            if elem_id and elem_id in id_map:
                rel_path = convert_to_relative_path(id_map[elem_id], html_path)
                # 이미지 삽입도 동일 블록에 추가
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

    # 최종 MD 파일 생성: blocks 리스트를 줄바꿈으로 합침
    final_md = "\n\n".join(blocks)
    out_md_path = html_path.replace(".html", "_converted.md")
    with open(out_md_path, "w", encoding="utf-8") as f:
        f.write(final_md)

    print(f"✅ HTML -> MD 변환 완료: {out_md_path}")
    return out_md_path

if __name__ == "__main__":
    # 예시: 인자로 HTML 파일, 이미지 경로 리스트, 그리고 result JSON (여기서는 result는 사용하지 않음) 전달
    html_to_md("path/to/your_file.html", ["path/to/image1.png", "path/to/image2.png"], result={})
