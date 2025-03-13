import os
import re
import sys
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
            elem_id = match.group(1)  # '7'
            id_map[elem_id] = img_path
    return id_map

def get_page_info(element):
    """요소의 data-page 속성이 있다면 [Page: X] 문자열을 반환"""
    page = element.get("data-page")
    return f"[Page: {page}]" if page else ""

def html_to_md(html_path, images_paths):
    """
    - chart, table, figure 등은 이미지 삽입은 elements id 기반으로 처리
    - <table>은 parse_html_table_to_md()를 사용해 Markdown 표 생성
    - 각 HTML 태그 처리 시, data-page 속성이 있으면 해당 페이지 정보를 Markdown에 포함
    - HTML 태그별 끝날 때마다 "<<BLOCKEND>>" 삽입
    - 연속된 <<BLOCKEND>> 사이에 공백/빈줄만 있으면 하나만 남김
    """
    if not os.path.exists(html_path):
        print(f"❌ HTML 파일을 찾을 수 없습니다: {html_path}")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")
    body = soup.body if soup.body else soup

    # build {id -> 이미지 경로}
    id_map = build_id_image_map(images_paths)

    md_output = []

    def get_text_content(element):
        text = element.get_text(separator="\n")
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        return text.strip()

    # 공통: data-page 정보를 별도 줄에 추가
    def append_with_page_info(element, text):
        page_info = get_page_info(element)
        if page_info:
            md_output.append(page_info)
        if text:
            md_output.append(text)
        md_output.append("<<BLOCKEND>>")

    for elem in body.find_all(recursive=False):
        tagname = elem.name.lower()

        if tagname in ["p", "header", "h1", "h2", "h3", "h4", "h5", "h6"]:
            content = get_text_content(elem)
            append_with_page_info(elem, content)

        elif tagname == "br":
            md_output.append("")
            md_output.append("<<BLOCKEND>>")

        elif tagname == "table":
            md_table = parse_html_table_to_md(elem)
            lines = md_table.split("\n")
            if len(lines) >= 2:
                col_count = lines[0].count("|") - 1
                sep_line = "| " + " | ".join(["---"] * col_count) + " |"
                lines.insert(1, sep_line)
            md_table_fixed = "\n".join(lines).strip()
            if md_table_fixed:
                append_with_page_info(elem, md_table_fixed)
            caption = elem.find("caption")
            if caption:
                cap_text = caption.get_text(strip=True)
                if cap_text:
                    md_output.append(f"**{cap_text}**")
            elem_id = elem.get("id")
            if elem_id and elem_id in id_map:
                rel_path = convert_to_relative_path(id_map[elem_id], html_path)
                md_output.append(f"![id_{elem_id}]({rel_path})")
            md_output.append("<<BLOCKEND>>")

        elif tagname == "img":
            src = elem.get("src", "")
            if not src:
                elem_id = elem.get("id", "")
                if elem_id and elem_id in id_map:
                    src = id_map[elem_id]
            rel_path = convert_to_relative_path(src, html_path) if src else ""
            md_output.append(f"![]({rel_path})")
            alt_text = elem.get("alt", "")
            if alt_text:
                md_output.append(f"*{alt_text}*")
            append_with_page_info(elem, "")
            
        elif tagname == "figure":
            img = elem.find("img")
            if img:
                src = img.get("src", "")
                if not src:
                    figure_id = elem.get("id", "")
                    if figure_id and figure_id in id_map:
                        src = id_map[figure_id]
                rel_path = convert_to_relative_path(src, html_path) if src else ""
                md_output.append(f"![]({rel_path})")
                alt_text = img.get("alt", "")
                if alt_text:
                    md_output.append(f"*{alt_text}*")
            else:
                figure_id = elem.get("id", "")
                if figure_id and figure_id in id_map:
                    rel_path = convert_to_relative_path(id_map[figure_id], html_path)
                    md_output.append(f"![]({rel_path})")
            figcaption = elem.find("figcaption")
            if figcaption:
                caption = get_text_content(figcaption)
                md_output.append("#### " + caption)
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
                    md_output.append(md_table_fixed)
            append_with_page_info(elem, "")
            
        else:
            elem_id = elem.get("id")
            if elem_id and elem_id in id_map:
                rel_path = convert_to_relative_path(id_map[elem_id], html_path)
                md_output.append(f"![id_{elem_id}]({rel_path})")
            content = get_text_content(elem)
            append_with_page_info(elem, content)

    # 중복 <<BLOCKEND>> 정리
    cleaned_output = []
    i = 0
    while i < len(md_output):
        line = md_output[i].strip()
        if line == "<<BLOCKEND>>":
            j = i + 1
            while j < len(md_output) and md_output[j].strip() in ["", "<<BLOCKEND>>"]:
                j += 1
            cleaned_output.append("<<BLOCKEND>>")
            i = j
        else:
            cleaned_output.append(md_output[i])
            i += 1

    final_md = "\n\n".join(seg for seg in cleaned_output if seg.strip())
    out_md_path = html_path.replace(".html", "_converted.md")
    with open(out_md_path, "w", encoding="utf-8") as f:
        f.write(final_md)

    print(f"✅ HTML -> MD 변환 완료: {out_md_path}")
    return out_md_path
