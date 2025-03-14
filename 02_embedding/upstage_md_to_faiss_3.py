import os
import re
import json
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

def split_into_blocks(text, delimiter="<<BLOCKEND>>"):
    """
    텍스트를 delimiter(기본값: '<<BLOCKEND>>')를 기준으로 분할하고,
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
    (실제 임베딩을 직접 계산하진 않습니다. FAISS.from_documents 사용 시,
    LangChain 내부적으로 임베딩 모델을 통해 벡터화하므로 여기서는 텍스트와 메타데이터만 준비합니다.)
    """
    texts = []
    element_ids = []
    for block in blocks:
        text_content, elem_id = parse_block(block)
        texts.append(text_content)
        element_ids.append(elem_id)
    return texts, element_ids

def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("ERROR: OPENAI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")
    FOLDER_PATH=r"C:\Users\yoyo2\fas\RAG_Pre_processing\01_pre-processing\upstage_document_parse\temp\250314-14-42_20241220_[교재]_연말정산 세무_이석정_한국_회원_3.5시간65~68"
    # OpenAI 임베딩 모델 객체 생성 (원하는 모델명으로 교체 가능)
    # 모델 이름이 "text-embedding-3-small"이면, 실제 호출은 "text-embedding-3-small" API를 사용합니다.
    embedding_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=api_key
    )
    
    # 사용자가 임베딩할 폴더 경로 입력
    folder_path = FOLDER_PATH
    
    # _converted.md 파일 찾기
    md_file = None
    for fname in os.listdir(folder_path):
        if fname.endswith("_converted.md"):
            md_file = os.path.join(folder_path, fname)
            break
    if not md_file:
        raise FileNotFoundError("ERROR: _converted.md 파일을 찾을 수 없습니다.")
    print(f"[main] _converted.md 파일 경로: {md_file}")
    
    # _metadata.json 파일 로드
    metadata_json = load_metadata_json(folder_path)
    if not metadata_json:
        print("[main] 메타데이터 JSON이 비어 있거나 찾을 수 없습니다.")
    
    # MD 파일 텍스트 로드
    text = load_md_file(md_file)
    print(f"[main] MD 파일 길이: {len(text)}")
    
    # 텍스트를 블록으로 분할
    blocks = split_into_blocks(text, delimiter="<<BLOCKEND>>")
    print(f"[main] 분할된 블록 수: {len(blocks)}")
    
    # 블록별로 텍스트와 elementId를 추출
    texts, element_ids = embed_blocks(blocks)
    print(f"[main] 준비된 텍스트 개수: {len(texts)}")
    
    # Document 객체 리스트 생성
    documents = []
    for i, text_content in enumerate(texts):
        elem_id = element_ids[i]
        
        # element_id 기반으로 메타데이터 검색
        meta = {}
        if elem_id and elem_id in metadata_json:
            meta = metadata_json[elem_id]
        
        # Document 생성 (page_content와 metadata)
        doc = Document(page_content=text_content, metadata=meta)
        documents.append(doc)
    
    # FAISS 벡터스토어 생성
    # from_texts(...) 대신 from_documents(...) 사용
    vectorstore = FAISS.from_documents(
        documents=documents,
        embedding=embedding_model
    )
    
    # 벡터스토어를 지정한 경로에 저장
    save_path = "vdb/faiss_index"
    vectorstore.save_local(save_path)
    print(f"Vectorstore 저장 완료: {save_path}")

if __name__ == "__main__":
    main()
