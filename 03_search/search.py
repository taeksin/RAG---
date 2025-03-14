import streamlit as st
import os
import numpy as np
import pandas as pd

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai.embeddings import OpenAIEmbeddings

from sklearn.decomposition import PCA
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# 상수 설정
# -----------------------------
VDB_INDEX_PATH = "vdb/faiss_index/small/4_upstage_layout"  # FAISS 인덱스 경로


# -----------------------------
# 시각화 함수들 (2D/3D)
# -----------------------------
def visualize_embeddings_2d(embeddings_array, texts, query_text=None, query_embedding=None):
    """
    embeddings_array: (N, D) 형태의 넘파이 배열
    texts: 길이 N인 텍스트 리스트 (라벨용)
    query_text: 쿼리 텍스트
    query_embedding: (1, D) 형태의 넘파이 배열
    """
    pca = PCA(n_components=2)
    reduced = pca.fit_transform(embeddings_array)
    
    df = pd.DataFrame(reduced, columns=["PC1", "PC2"])
    df["text"] = [t[:15] for t in texts]  # 표시할 때 너무 길지 않게 앞부분만

    fig = px.scatter(
        df,
        x="PC1",
        y="PC2",
        text="text",
        title="검색 결과 임베딩 2D 시각화 (PCA)"
    )
    fig.update_traces(textposition="top center", marker=dict(size=6))

    # 쿼리 포인트 시각화
    if query_text and query_embedding is not None:
        query_reduced = pca.transform(query_embedding)
        fig.add_trace(
            go.Scatter(
                x=[query_reduced[0, 0]],
                y=[query_reduced[0, 1]],
                mode="markers+text",
                marker=dict(size=8, color="red"),
                text=[query_text],
                name="Query"
            )
        )

    return fig


def visualize_embeddings_3d(embeddings_array, texts, query_text=None, query_embedding=None):
    """
    embeddings_array: (N, D) 형태의 넘파이 배열
    texts: 길이 N인 텍스트 리스트 (라벨용)
    query_text: 쿼리 텍스트
    query_embedding: (1, D) 형태의 넘파이 배열
    """
    pca = PCA(n_components=3)
    reduced = pca.fit_transform(embeddings_array)
    
    df = pd.DataFrame(reduced, columns=["PC1", "PC2", "PC3"])
    df["text"] = [t[:15] for t in texts]

    fig = px.scatter_3d(
        df,
        x="PC1",
        y="PC2",
        z="PC3",
        text="text",
        title="검색 결과 임베딩 3D 시각화 (PCA)"
    )
    fig.update_traces(textposition="top center", marker=dict(size=5))

    # 쿼리 포인트 시각화
    if query_text and query_embedding is not None:
        query_reduced = pca.transform(query_embedding)
        fig.add_trace(
            go.Scatter3d(
                x=[query_reduced[0, 0]],
                y=[query_reduced[0, 1]],
                z=[query_reduced[0, 2]],
                mode="markers+text",
                marker=dict(size=6, color="red"),
                text=[query_text],
                name="Query"
            )
        )

    return fig


# -----------------------------
# 메인 Streamlit 앱
# -----------------------------
def main():
    st.title("FAISS 벡터 검색 + 2D/3D 시각화 (전체 문서 검색)")

    # .env 로드 및 API KEY 확인
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("ERROR: OPENAI_API_KEY가 설정되어 있지 않습니다.")
        return

    # 임베딩 모델 생성
    embedding_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=api_key
    )

    # FAISS 인덱스 로드
    try:
        vectorstore = FAISS.load_local(
            folder_path=VDB_INDEX_PATH,
            embeddings=embedding_model,
            allow_dangerous_deserialization=True
        )
    except Exception as e:
        st.error(f"벡터스토어 로드 중 오류가 발생했습니다: {str(e)}")
        return

    # ★ FAISS 인덱스에 저장된 전체 벡터 개수
    faiss_index_size = vectorstore.index.ntotal  # 인덱스의 전체 벡터(문서) 개수

    # 검색어 입력
    query = st.text_input("검색어를 입력하세요:")

    # 검색 실행
    if st.button("검색 실행") or query:
        if query.strip():
            try:
                # (1) 인덱스 전체를 검색 (k=faiss_index_size)
                docs_with_score = vectorstore.similarity_search_with_score(query, k=faiss_index_size)

                st.write(f"**검색 질의:** {query}")
                st.write(f"**결과 개수:**  전체 {faiss_index_size}개")

                # (2) 표 생성: content, metadata, score 열
                rows = []
                for (doc, score) in docs_with_score:
                    rows.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": score
                    })
                df = pd.DataFrame(rows)

                # (3) 표 출력 (컬럼 클릭으로 정렬 가능)
                st.dataframe(df)

                # (4) 2D/3D 시각화: 검색된 문서들의 임베딩 계산 후 PCA
                #    문서가 매우 많다면(수천/수만 건) 성능에 유의!
                contents_list = df["content"].tolist()
                doc_embeddings_list = embedding_model.embed_documents(contents_list)
                doc_embeddings = np.array(doc_embeddings_list)

                query_embed = embedding_model.embed_documents([query])
                query_embed = np.array(query_embed)

                # (5) 탭 UI로 2D, 3D 시각화
                tab2d, tab3d = st.tabs(["2D 시각화", "3D 시각화"])
                
                with tab2d:
                    fig_2d = visualize_embeddings_2d(
                        embeddings_array=doc_embeddings,
                        texts=contents_list,
                        query_text=query,
                        query_embedding=query_embed
                    )
                    st.plotly_chart(fig_2d, use_container_width=True)

                with tab3d:
                    fig_3d = visualize_embeddings_3d(
                        embeddings_array=doc_embeddings,
                        texts=contents_list,
                        query_text=query,
                        query_embedding=query_embed
                    )
                    st.plotly_chart(fig_3d, use_container_width=True)

            except Exception as e:
                st.error(f"검색 중 오류가 발생했습니다: {str(e)}")
        else:
            st.warning("검색어를 입력해주세요.")

if __name__ == "__main__":
    main()
