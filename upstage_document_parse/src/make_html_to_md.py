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

def make_html_to_md(html_path, images_paths):
    """
    - chart_candidates, table_candidates, figure_candidates 제거
        (이미지 삽입은 elements id 기반으로만 처리)
    - <table>은 parse_html_table_to_md()를 사용해 Markdown 표 생성
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

    for elem in body.find_all(recursive=False):
        tagname = elem.name

        if tagname == "p":
            content = get_text_content(elem)
            if content:
                md_output.append(content)
            md_output.append("<<BLOCKEND>>")

        elif tagname == "br":
            md_output.append("")
            md_output.append("<<BLOCKEND>>")

        elif tagname == "table":
            # 1) HTML 테이블 -> parse_html_table_to_md()
            md_table = parse_html_table_to_md(elem)
            # 2) 첫 행 헤더 구분 라인 추가
            lines = md_table.split("\n")
            if len(lines) >= 2:
                col_count = lines[0].count("|") - 1
                sep_line = "| " + " | ".join(["---"] * col_count) + " |"
                lines.insert(1, sep_line)
            md_table_fixed = "\n".join(lines).strip()
            if md_table_fixed:
                md_output.append(md_table_fixed)
            # 태그 id가 있을 경우, 해당 이미지 삽입 (ex: '3_page_1_table_1.png')
            elem_id = elem.get("id")
            if elem_id and elem_id in id_map:
                rel_path = convert_to_relative_path(id_map[elem_id], html_path)
                md_output.append(f"![id_{elem_id}]({rel_path})")
            md_output.append("<<BLOCKEND>>")

        elif tagname == "img":
            # 단독 <img> 태그 처리: 이미지 삽입 후 alt 속성이 있으면 별도의 줄에 캡션 추가
            src = elem.get("src", "")
            if not src:
                # src가 없으면 해당 태그의 id를 이용해 이미지 경로 추출
                elem_id = elem.get("id", "")
                if elem_id and elem_id in id_map:
                    src = id_map[elem_id]
            rel_path = convert_to_relative_path(src, html_path) if src else ""
            md_output.append(f"![]({rel_path})")
            alt_text = elem.get("alt", "")
            if alt_text:
                md_output.append(f"*{alt_text}*")
            md_output.append("<<BLOCKEND>>")

        elif tagname == "figure":
            # <figure> 태그 처리: 내부 <img> 태그와 figcaption 처리
            img = elem.find("img")
            if img:
                src = img.get("src", "")
                if not src:
                    # src가 없으면 figure 태그의 id를 이용해 이미지 경로 추출
                    figure_id = elem.get("id", "")
                    if figure_id and figure_id in id_map:
                        src = id_map[figure_id]
                rel_path = convert_to_relative_path(src, html_path) if src else ""
                md_output.append(f"![]({rel_path})")
                alt_text = img.get("alt", "")
                if alt_text:
                    md_output.append(f"*{alt_text}*")
            else:
                # img 태그가 없으면, figure 태그의 id로 이미지 삽입 시도
                figure_id = elem.get("id", "")
                if figure_id and figure_id in id_map:
                    rel_path = convert_to_relative_path(id_map[figure_id], html_path)
                    md_output.append(f"![]({rel_path})")
            # figcaption 처리: 있으면 h4 헤딩으로 추가
            figcaption = elem.find("figcaption")
            if figcaption:
                caption = get_text_content(figcaption)
                md_output.append("#### " + caption)
            md_output.append("<<BLOCKEND>>")

        else:
            # 기타 태그 (figure, div, etc.)
            # id가 있으면, 그 id의 이미지를 삽입
            elem_id = elem.get("id")
            if elem_id and elem_id in id_map:
                # 이미지를 먼저 넣고
                rel_path = convert_to_relative_path(id_map[elem_id], html_path)
                md_output.append(f"![id_{elem_id}]({rel_path})")

            # 텍스트 처리
            content = get_text_content(elem)
            if content:
                md_output.append(content)
            md_output.append("<<BLOCKEND>>")

    # 연속된 <<BLOCKEND>> 사이에 공백/빈줄만 있으면 하나만 남김
    cleaned_output = []
    i = 0
    while i < len(md_output):
        line = md_output[i].strip()
        if line == "<<BLOCKEND>>":
            j = i + 1
            while j < len(md_output):
                next_line = md_output[j].strip()
                if not next_line or next_line == "<<BLOCKEND>>":
                    j += 1
                    continue
                break
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
