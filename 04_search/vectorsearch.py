import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from langchain_community.vectorstores import FAISS
import streamlit as st
from config import get_document
from custom_embeddings import CustomEmbeddings

def load_vectorstore(vdb_index_path: str, selected_embedding: str):
    """
    주어진 벡터스토어 경로와 선택된 임베딩 모델에 따라 FAISS 벡터스토어를 로드합니다.
    
    임베딩은 CustomEmbeddings 객체를 사용합니다.
    
    Args:
        vdb_index_path (str): FAISS 벡터스토어가 저장된 폴더 경로.
        selected_embedding (str): 선택된 임베딩 모델 ("upstage_passage" 또는 "openai_small").
    
    Returns:
        FAISS: 로드된 FAISS 벡터스토어 객체.
    """
    embedding_obj = CustomEmbeddings(selected_embedding)
    return FAISS.load_local(
         folder_path=vdb_index_path,
         embeddings=embedding_obj,
         allow_dangerous_deserialization=True
    )

def search_query_vectorstore(query: str, selected_embedding: str, vectorstore: FAISS, db_embeddings: np.ndarray):
    """
    주어진 쿼리에 대해 벡터스토어 내의 모든 문서를 검색하고,
    결과를 (L2 거리, 코사인 유사도, 텍스트, 메타데이터) 순서의 튜플 리스트로 반환합니다.
    
    Args:
        query (str): 사용자 입력 쿼리.
        selected_embedding (str): 선택된 임베딩 모델 식별자.
        vectorstore (FAISS): 로드된 FAISS 벡터스토어 객체.
        db_embeddings (np.ndarray): DB 문서 임베딩 배열.
    
    Returns:
        tuple: (results, query_vector)
            - results: 각 결과가 (L2 거리, 코사인 유사도, 텍스트, 메타데이터)인 튜플 리스트.
            - query_vector: 쿼리 텍스트의 임베딩 벡터 (numpy 배열).
    """
    # CustomEmbeddings 객체를 생성하여 쿼리 임베딩 생성
    embedding_obj = CustomEmbeddings(selected_embedding)
    query_embedding = embedding_obj.embed_query(query)
    if query_embedding is None:
        st.error("쿼리 임베딩 생성 실패")
        return [], None
    query_vector = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
    
    # 전체 문서를 대상으로 검색 (k = vectorstore.index.ntotal)
    k = vectorstore.index.ntotal
    distances, indices = vectorstore.index.search(query_vector, k)
    cos_sim_all = cosine_similarity(db_embeddings, query_vector).flatten()
    
    results = []
    for distance, idx in zip(distances[0], indices[0]):
        doc_id = vectorstore.index_to_docstore_id[idx]
        doc = get_document(vectorstore.docstore, doc_id)
        cosine_value = cos_sim_all[idx]
        results.append((distance, cosine_value, doc.page_content, doc.metadata))
    return results, query_vector
