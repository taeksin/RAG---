# merge_markdown_captions.py
import os
import re
import sys

def merge_captions_into_md(base_folder):
    """
    base_folder 내에서 _converted.md 파일을 찾아, 
    해당 파일 내 이미지 참조 아래에 Items 폴더의 캡션 파일 내용을 삽입한 새로운 markdown 파일(_merged.md)을 생성합니다.
    """
    # _converted.md 파일 찾기
    md_file = None
    for fname in os.listdir(base_folder):
        if fname.endswith("_converted.md"):
            md_file = os.path.join(base_folder, fname)
            break
    if not md_file:
        print("[merge_captions_into_md] 에러: _converted.md 파일을 찾을 수 없습니다.")
        return

    # Items 폴더 경로 설정
    items_folder = os.path.join(base_folder, "Items")
    if not os.path.exists(items_folder):
        print(f"[merge_captions_into_md] 에러: Items 폴더가 존재하지 않습니다: {items_folder}")
        return

    # _converted.md 파일 읽기
    with open(md_file, "r", encoding="utf-8") as f:
        md_lines = f.readlines()

    merged_lines = []
    # 이미지 참조 패턴: ![](./Items/파일명.png)
    image_pattern = re.compile(r'!\[\]\(\./Items/([^)]*\.png)\)')

    for line in md_lines:
        merged_lines.append(line)
        match = image_pattern.search(line)
        if match:
            image_filename = match.group(1)
            caption_filename = os.path.join(items_folder, f"{os.path.splitext(image_filename)[0]}_caption.txt")
            if os.path.exists(caption_filename):
                with open(caption_filename, "r", encoding="utf-8") as cf:
                    caption_text = cf.read().strip()
                if caption_text:
                    # 이미지 참조 아래에 캡션 추가 (빈 줄로 구분)
                    merged_lines.append("\n")
                    merged_lines.append(caption_text + "\n")
                    merged_lines.append("\n")
                else:
                    print("[merge_captions_into_md] 캡션 파일이 비어 있음.")
            else:
                print("[merge_captions_into_md] 캡션 파일을 찾을 수 없음.")
    
    # 새 파일(_merged.md)로 저장
    merged_md_file = md_file.replace("_converted.md", "_converted.md")
    with open(merged_md_file, "w", encoding="utf-8") as f:
        f.writelines(merged_lines)
    print(f"최종 병합된 markdown 파일 생성됨 :\n  -> {merged_md_file}")
    return merged_md_file

if __name__ == "__main__":
    base_folder = "pre-processing/upstage_document_parse/temp/250312-18-12_모니터6~7p"
    merge_captions_into_md(base_folder)
