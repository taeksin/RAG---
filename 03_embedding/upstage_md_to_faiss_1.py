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
        # metadata에 elementId가 포함되어 있다고 가정 (없으면 빈 문자열)
        elem_id = doc.metadata.get("elementId", "")
        # metadata를 JSON 문자열로 변환 (키가 문자열이 아니면 변환 과정에서 에러가 날 수 있으므로 주의)
        meta_str = json.dumps(doc.metadata, ensure_ascii=False)
        data.append({
            "elementId": elem_id,
            "page_content": doc.page_content,
            "metadata": meta_str
        })
    df = pd.DataFrame(data)
    df.to_excel(excel_fname, index=False)
    print(f"엑셀 파일 저장 완료: {excel_fname}")

def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("ERROR: OPENAI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")
    
    # 임베딩할 파일이 있는 폴더 경로를 지정합니다.
    FOLDER_PATH = r"C:\Users\yoyo2\fas\RAG_Pre_processing\01_pre-processing\upstage_document_parse\temp\250314-17-45_모니터1~3p"
    folder_path = FOLDER_PATH

    # 폴더 내에서 "01_"로 시작하고 "_merged.md"로 끝나는 파일 찾기
    md_file = None
    for fname in os.listdir(folder_path):
        if fname.startswith("01_") and fname.endswith("_merged.md"):
            md_file = os.path.join(folder_path, fname)
            break
    if not md_file:
        raise FileNotFoundError("ERROR: '01_'로 시작하고 '_merged.md'로 끝나는 파일을 찾을 수 없습니다.")
    
    # _metadata.json 파일 로드
    metadata_json = load_metadata_json(folder_path)
    if not metadata_json:
        print("[main] 메타데이터 JSON이 비어 있거나 찾을 수 없습니다.")
    
    # MD 파일 텍스트 로드
    text = load_md_file(md_file)
    
    # 텍스트를 블록으로 분할 (delimiter: <<SPLIT>>)
    blocks = split_into_blocks(text, delimiter="<<SPLIT>>")
    # 블록별로 텍스트와 elementId를 추출
    texts, element_ids = embed_blocks(blocks)
    print(f"[main] 분할된 블록 수: {len(blocks)}, 준비된 텍스트 개수: {len(texts)}")
    
    # Document 객체 리스트 생성 (각 Document에는 page_content와 metadata가 포함됨)
    documents = []
    for i, text_content in enumerate(texts):
        elem_id = element_ids[i]
        
        # element_id 기반으로 메타데이터 검색
        meta = {}
        if elem_id and elem_id in metadata_json:
            meta = metadata_json[elem_id]
        # Document의 metadata에 원본 elementId와 page_content를 포함시키기
        meta["elementId"] = elem_id if elem_id is not None else ""
        meta["page_content"] = text_content  # page_content도 메타데이터에 추가
        doc = Document(page_content=text_content, metadata=meta)
        documents.append(doc)
    
    # OpenAI 임베딩 모델 객체 생성 (원하는 모델명으로 교체 가능)
    embedding_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=api_key
    )
    
    # FAISS 벡터스토어 생성 (문서에서 임베딩 벡터를 계산)
    vectorstore = FAISS.from_documents(
        documents=documents,
        embedding=embedding_model
    )
    
    # 벡터스토어를 지정한 경로에 저장
    save_path = "vdb/faiss_index/small/01_upstageLayout"
    vectorstore.save_local(save_path)
    print(f"Vectorstore 저장 완료: {save_path}")
    
    # 임베딩에 사용된 문서들을 엑셀 파일로 저장
    # md_file의 파일명을 이용하여 확장자를 .xlsx로 변경
    base_fname = os.path.basename(md_file)
    excel_fname = os.path.splitext(base_fname)[0] + ".xlsx"
    excel_path = os.path.join(folder_path, excel_fname)
    create_excel_from_documents(documents, excel_path)

if __name__ == "__main__":
    main()
