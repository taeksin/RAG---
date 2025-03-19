import os
import json
import re
import pandas as pd
import threading

# Excel 쓰기 작업을 위한 전역 Lock 객체
excel_lock = threading.Lock()

def load_md_file(md_path):
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"ERROR: 파일 '{md_path}'이 존재하지 않습니다.")
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()
    return text

def load_metadata_json(folder_path):
    for fname in os.listdir(folder_path):
        if fname.endswith("_metadata.json"):
            meta_path = os.path.join(folder_path, fname)
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
    print("메타데이터 JSON 파일을 찾을 수 없습니다.")
    return {}

def split_into_blocks(text, delimiter="<<SPLIT>>"):
    blocks = [block.strip() for block in text.split(delimiter)]
    blocks = [block for block in blocks if block]
    return blocks

def parse_block(block):
    lines = block.strip().splitlines()
    element_id = None
    if lines:
        first_line = lines[0].strip()
        match = re.match(r'elementId:\s*(\S+)', first_line)
        if match:
            element_id = match.group(1)
            lines = lines[1:]
    text_content = "\n".join(lines).strip()
    return text_content, element_id

def embed_blocks(blocks):
    texts = []
    element_ids = []
    for block in blocks:
        text_content, elem_id = parse_block(block)
        texts.append(text_content)
        element_ids.append(elem_id)
    return texts, element_ids

def save_md_to_excel(md_path, indicator, excel_path):
    """
    md 파일을 읽어 블록 단위로 분할한 후, 각 블록에 대해
    파일명, page_content, metadata를 포함하는 데이터를 생성하여
    Excel 파일에 저장합니다.
    
    indicator가 "first"이면 해당 Excel 파일이 이미 존재할 경우 삭제한 후 새로 생성하고,
    그렇지 않으면 기존 파일에 데이터를 추가(행 단위)합니다.
    indicator는 처리 중인 파일의 순서를 나타냅니다.
    """
    folder_path = os.path.dirname(md_path)
    metadata_json = load_metadata_json(folder_path)
    text = load_md_file(md_path)
    blocks = split_into_blocks(text, delimiter="<<SPLIT>>")
    texts, element_ids = embed_blocks(blocks)
    
    # md 파일명 추출 (파일명만, 확장자 포함)
    file_name = os.path.basename(md_path)
    
    # 각 블록에 대해 문서 정보를 생성 (파일명, page_content, metadata)
    docs = []
    for i, text_content in enumerate(texts):
        elem_id = element_ids[i]
        meta = {}
        if elem_id and metadata_json and elem_id in metadata_json:
            meta = metadata_json[elem_id]
        meta["elementId"] = elem_id if elem_id is not None else ""
        meta["page_content"] = text_content
        docs.append({
            "파일명": file_name,
            "page_content": text_content,
            "metadata": json.dumps(meta, ensure_ascii=False)
        })
    
    df = pd.DataFrame(docs)
    df = df[["파일명", "page_content", "metadata"]]
    # 중복된 page_content 제거
    df = df.drop_duplicates(subset=["page_content"])
    
    with excel_lock:
        # indicator가 "first"이면 기존 Excel 파일이 있다면 삭제
        if indicator.lower() == "first" and os.path.exists(excel_path):
            os.remove(excel_path)
        # 파일이 존재하면 기존 데이터에 행을 추가, 없으면 새로 생성
        if os.path.exists(excel_path):
            df_existing = pd.read_excel(excel_path)
            df_new = pd.DataFrame(docs)
            df_new = df_new[["파일명", "page_content", "metadata"]]
            df_concat = pd.concat([df_existing, df_new], ignore_index=True)
            df_concat = df_concat[["파일명", "page_content", "metadata"]]
            # 중복 제거: 중복된 page_content 제거
            df_concat = df_concat.drop_duplicates(subset=["page_content"])
            df_concat.to_excel(excel_path, index=False)
        else:
            df.to_excel(excel_path, index=False)
        # indicator가 "final"일 때만 출력
        if indicator.lower() == "final":
            print(f"[엑셀 저장 완료] {excel_path}")
