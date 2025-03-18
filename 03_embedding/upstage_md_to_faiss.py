import os
import re
import json
import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from dotenv import load_dotenv

def load_md_file(md_path):
    """
    지정한 md 파일의 전체 텍스트를 로드합니다.
    """
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"ERROR: 파일 '{md_path}'이 존재하지 않습니다.")
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()
    return text

def load_metadata_json(folder_path):
    """
    folder_path 내에서 _metadata.json으로 끝나는 파일을 찾아 로드합니다.
    반환되는 데이터는 {elementId: metadata, ...} 형식의 dict입니다.
    """
    for fname in os.listdir(folder_path):
        if fname.endswith("_metadata.json"):
            meta_path = os.path.join(folder_path, fname)
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
    print("메타데이터 JSON 파일을 찾을 수 없습니다.")
    return {}

def split_into_blocks(text, delimiter="<<SPLIT>>"):
    """
    텍스트를 delimiter(기본값: '<<SPLIT>>')를 기준으로 분할하고,
    빈 블록은 제거합니다.
    """
    blocks = [block.strip() for block in text.split(delimiter)]
    blocks = [block for block in blocks if block]
    return blocks

def parse_block(block):
    """
    블록의 첫 번째 줄에 있는 'elementId: <id>'를 추출하고,
    해당 줄을 제거한 나머지 텍스트와 elementId를 반환합니다.
    만약 elementId가 없으면 None을 반환합니다.
    """
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
    """
    블록을 순회하며 parse_block으로 (텍스트, elementId)를 추출합니다.
    """
    texts = []
    element_ids = []
    for block in blocks:
        text_content, elem_id = parse_block(block)
        texts.append(text_content)
        element_ids.append(elem_id)
    return texts, element_ids

def create_excel_from_documents(documents, excel_fname):
    """
    Document 객체 리스트로부터 elementId, page_content, metadata를 추출하여 엑셀 파일로 저장합니다.
    metadata는 JSON 문자열 형태로 저장합니다.
    """
    data = []
    for doc in documents:
        elem_id = doc.metadata.get("elementId", "")
        meta_str = json.dumps(doc.metadata, ensure_ascii=False)
        data.append({
            "elementId": elem_id,
            "page_content": doc.page_content,
            "metadata": meta_str
        })
    df = pd.DataFrame(data)
    df.to_excel(excel_fname, index=False)

def embedding_md_to_faiss(md_path):
    """
    md 파일 경로를 매개변수로 받아, 해당 파일의 텍스트를 로드하고
    메타데이터 JSON을 로드한 후 임베딩 처리와 엑셀 파일 생성을 수행합니다.
    
    FAISS 벡터스토어를 생성하여 저장하고, 생성된 FAISS 저장 경로와 엑셀 파일 경로를 dict로 반환합니다.
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("ERROR: OPENAI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")
    
    # md 파일이 있는 폴더 경로
    folder_path = os.path.dirname(md_path)
    
    # 메타데이터 로드
    metadata_json = load_metadata_json(folder_path)
    if not metadata_json:
        print("[process_md_file] 메타데이터 JSON이 비어 있거나 찾을 수 없습니다.")
    
    # MD 파일 텍스트 로드
    text = load_md_file(md_path)
    
    # 텍스트를 블록으로 분할
    blocks = split_into_blocks(text, delimiter="<<SPLIT>>")
    texts, element_ids = embed_blocks(blocks)
    # print(f"[process_md_file] 분할된 블록 수: {len(blocks)}, 준비된 텍스트 개수: {len(texts)}")
    
    # Document 리스트 생성
    documents = []
    for i, text_content in enumerate(texts):
        elem_id = element_ids[i]
        meta = {}
        if elem_id and elem_id in metadata_json:
            meta = metadata_json[elem_id]
        meta["elementId"] = elem_id if elem_id is not None else ""
        meta["page_content"] = text_content
        doc = Document(page_content=text_content, metadata=meta)
        documents.append(doc)
    
    # OpenAI 임베딩 모델 객체 생성
    embedding_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=api_key
    )
    
    # FAISS 벡터스토어 생성
    vectorstore = FAISS.from_documents(
        documents=documents,
        embedding=embedding_model
    )
    
    # md 파일 이름에서 01, 02, 03, 04 등 숫자 추출
    base_fname = os.path.basename(md_path)
    # 정규표현식으로 파일명 시작 부분의 숫자를 찾음 (예: "01_", "02_", "03_", "04_" 등)
    match = re.match(r'^(\d+)_', base_fname)
    prefix_number = match.group(1) if match else "00"
    
    # prefix_number에 따라 다른 폴더명
    mapping = {
        "01": "01_upstageLayout",
        "02": "02_upstageLayout_overlap_1",
        "03": "03_upstageLayout_overlap_2",
        "04": "04_Nsplit"
    }
    
    # 매핑에서 찾으면 그 값을, 없으면 "00_unknown" 사용
    sub_folder = mapping.get(prefix_number, "00_unknown")
    
    # 최종 저장 경로
    save_path = os.path.join("vdb", "faiss_index", "small", sub_folder)
    os.makedirs(save_path, exist_ok=True)  # 폴더가 없으면 생성
    
    # FAISS 저장
    vectorstore.save_local(save_path)
    
    # 엑셀 파일 생성
    excel_fname = os.path.splitext(base_fname)[0] + ".xlsx"
    excel_path = os.path.join(folder_path, excel_fname)
    create_excel_from_documents(documents, excel_path)
    
    save_path = save_path.replace("\\", "/")
    excel_path = excel_path.replace("\\", "/")
    
    print("\n[임베딩 결과]")
    print(f"파일: {md_path}")
    print(f" → FAISS 경로: {save_path}")
    print(f" → EXCEL 경로: {excel_path}")
    
    return {"faiss_save_path": save_path, "excel_path": excel_path}

if __name__ == "__main__":
    # 테스트: md 파일 경로를 지정
    md_file_path = r"C:\Users\yoyo2\fas\RAG_Pre_processing\data\250318-16-00_모니터1p\02_250318-16-00_모니터1p_merged.md"
    result = embedding_md_to_faiss(md_file_path)
    print(result)
