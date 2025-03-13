# upstage_md_to_faiss.py
import os
import re
import json
import pickle
import numpy as np
import faiss
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

def load_md_file(md_path):
    """지정한 md 파일의 전체 텍스트를 로드합니다."""
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"ERROR: 파일 '{md_path}'이 존재하지 않습니다.")
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()
    return text

def split_into_blocks(text, delimiter="<<BLOCKEND>>"):
    """
    텍스트를 delimiter(기본 <<BLOCKEND>>)로 분할하고, 공백 블록은 제거합니다.
    """
    blocks = [block.strip() for block in text.split(delimiter)]
    # 공백인 블록 제거
    blocks = [block for block in blocks if block]
    return blocks

def parse_block(block):
    """
    블록에서 metadata 부분(존재하면)과 실제 텍스트를 분리합니다.
    metadata 부분은 "metadata:" 문자열 이후에 JSON 형식으로 되어 있다고 가정합니다.
    
    반환: (text_content, metadata_dict)
    - metadata_dict는 없으면 빈 dict를 반환
    """
    # metadata가 포함된 경우 "metadata:" 이후의 부분을 찾습니다.
    meta_match = re.search(r'metadata:\s*(\{.*?\})', block, re.DOTALL)
    metadata = {}
    if meta_match:
        meta_str = meta_match.group(1).strip()
        try:
            metadata = json.loads(meta_str)
        except Exception as e:
            print(f"[parse_block] metadata JSON 파싱 오류: {e}")
        # 제거: metadata 부분을 블록에서 제거
        text_content = re.sub(r'metadata:\s*\{.*?\}', '', block, flags=re.DOTALL).strip()
    else:
        text_content = block.strip()
    return text_content, metadata

def embed_blocks(blocks, embedding_model):
    """
    각 블록에 대해 임베딩을 생성하고, 블록의 텍스트와 임베딩 벡터를 리스트로 반환합니다.
    """
    texts = []
    metadata_list = []
    for block in blocks:
        text_content, metadata = parse_block(block)
        texts.append(text_content)
        metadata_list.append(metadata)
    # 임베딩 생성 (문서 임베딩)
    embeddings = embedding_model.embed_documents(texts)
    return texts, metadata_list, np.array(embeddings).astype("float32")

def save_faiss_index(index, mapping, save_dir, index_filename="faiss_index.idx", mapping_filename="faiss_mapping.pkl"):
    """
    faiss 인덱스와 매핑 데이터를 지정한 디렉토리에 저장합니다.
    """
    os.makedirs(save_dir, exist_ok=True)
    index_path = os.path.join(save_dir, index_filename)
    mapping_path = os.path.join(save_dir, mapping_filename)
    faiss.write_index(index, index_path)
    with open(mapping_path, "wb") as f:
        pickle.dump(mapping, f)
    print(f"FAISS 인덱스가 '{index_path}'에 저장되었습니다.")
    print(f"텍스트 매핑 데이터가 '{mapping_path}'에 저장되었습니다.")
    return index_path, mapping_path

def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("ERROR: OPENAI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")
    
    # 사용할 임베딩 모델 선택 ("small" 또는 "large")
    MODEL = "small"
    # 임베딩 모델 초기화 (text-embedding-3-{MODEL} 사용)
    embedding_model = OpenAIEmbeddings(model=f"text-embedding-3-{MODEL}", openai_api_key=api_key)
    
    # MD 파일 경로 (사용자가 입력)
    md_path = input("임베딩할 md 파일의 경로를 입력하세요: ").strip()
    print(f"[main] 입력된 md 파일 경로: {md_path}")
    
    text = load_md_file(md_path)
    print(f"[main] MD 파일 길이: {len(text)}")
    
    blocks = split_into_blocks(text)
    print(f"[main] 분할된 블록 수: {len(blocks)}")
    
    # 각 블록별 임베딩 생성
    texts, metadata_list, embeddings_array = embed_blocks(blocks, embedding_model)
    print(f"[main] 임베딩 벡터 shape: {embeddings_array.shape}")
    
    # FAISS 인덱스 생성 (L2 거리 사용)
    dim = embeddings_array.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings_array)
    print(f"[main] FAISS 인덱스에 {index.ntotal}개의 벡터가 추가되었습니다.")
    
    # 매핑 데이터: 각 임베딩에 해당하는 원본 텍스트와 metadata를 저장
    mapping = {"texts": texts, "metadata": metadata_list}
    
    # 인덱스와 매핑 저장
    save_dir = os.path.join("vdb", "faiss", MODEL)
    save_faiss_index(index, mapping, save_dir)
    
if __name__ == "__main__":
    main()
