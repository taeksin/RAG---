import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from langchain_community.vectorstores import FAISS
import streamlit as st

from upstage_embedding import get_upstage_embedding
from openai_embedding import get_openai_embedding
from config import get_document

def get_query_embedding(text, selected_embedding):
    """
    선택된 임베딩 모델에 따라 쿼리 텍스트를 임베딩합니다.
    """
    if selected_embedding == "upstage_passage":
        embedding = get_upstage_embedding(text, "passage")
        if embedding is None:
            st.error("쿼리 임베딩 생성 실패")
        return embedding
    elif selected_embedding == "openai_small":
        embedding = get_openai_embedding(text, "small")
        if embedding is None:
            st.error("쿼리 임베딩 생성 실패")
        return embedding

def load_vectorstore(vdb_index_path, selected_embedding):
    """
    주어진 벡터스토어 경로와 선택된 임베딩 모델에 따라 FAISS 벡터스토어를 로드합니다.
    """
    return FAISS.load_local(
         folder_path=vdb_index_path,
         embeddings=lambda text: get_query_embedding(text, selected_embedding),
         allow_dangerous_deserialization=True
    )

def search_query_vectorstore(query, selected_embedding, vectorstore, db_embeddings):
    """
    주어진 쿼리에 대해 벡터스토어 내 모든 문서를 검색한 후,
    결과를 (L2 거리, 코사인 유사도, 텍스트, 메타데이터) 순서의 튜플 리스트로 반환합니다.
    """
    query_embedding = get_query_embedding(query, selected_embedding)
    if query_embedding is None:
        st.error("쿼리 임베딩 생성 실패")
        return [], None
    query_vector = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
    
    k = vectorstore.index.ntotal  # 전체 문서를 대상으로 검색
    distances, indices = vectorstore.index.search(query_vector, k)
    cos_sim_all = cosine_similarity(db_embeddings, query_vector).flatten()
    
    results = []
    for distance, idx in zip(distances[0], indices[0]):
        doc_id = vectorstore.index_to_docstore_id[idx]
        doc = get_document(vectorstore.docstore, doc_id)
        cosine_value = cos_sim_all[idx]
        results.append((distance, cosine_value, doc.page_content, doc.metadata))
    return results, query_vector
