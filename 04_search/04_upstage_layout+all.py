import streamlit as st
import os
import numpy as np
import pandas as pd
import io
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai.embeddings import OpenAIEmbeddings

from sklearn.decomposition import PCA
import plotly.express as px
import plotly.graph_objects as go
from sklearn.metrics.pairwise import cosine_similarity

# -----------------------------
# 상수 설정
# -----------------------------
VDB_INDEX_PATH = "vdb/faiss_index/small/4_upstage_layout+all"  # FAISS 인덱스 경로

# -----------------------------
# 시각화 함수들 (2D/3D)
# -----------------------------
def visualize_embeddings_2d(embeddings_array, texts, query_text=None, query_embedding=None):
    pca = PCA(n_components=2)
    reduced = pca.fit_transform(embeddings_array)

    df = pd.DataFrame(reduced, columns=["X축", "Y축"])
    df["text"] = [t[:15] for t in texts]  # 표시용으로 텍스트 앞부분만 자름

    fig = px.scatter(
        df,
        x="X축",
        y="Y축",
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
    pca = PCA(n_components=3)
    reduced = pca.fit_transform(embeddings_array)

    df = pd.DataFrame(reduced, columns=["X축", "Y축", "Z축"])
    df["text"] = [t[:15] for t in texts]

    fig = px.scatter_3d(
        df,
        x="X축",
        y="Y축",
        z="Z축",
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
    st.title("Upstage layout으로 스플릿")

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("ERROR: OPENAI_API_KEY가 설정되어 있지 않습니다.")
        return

    # 임베딩 모델
    embedding_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=api_key
    )

    # 사이드바에 점수 설명 추가
    with st.sidebar:
        st.header("점수 계산 방식 안내")
        st.markdown("""
        **L2 Distance (Euclidean Distance)**  
        - 계산식: \\(\\|A - B\\| = \\sqrt{\\sum (A_i - B_i)^2} \\).  
        - **범위**: [0, ∞). 0에 가까울수록 유사함을 의미.
        ---
        **Cosine Similarity**  
        - 계산식: \\(\\frac{A \\cdot B}{\\|A\\| \\|B\\|}\\).  
        - **범위**: [-1, 1]. 1에 가까울수록 유사.
        ---
        **FAISS Score (옵션)**  
        - `similarity_search_with_score()` 반환값.  
        - 주로 IndexFlatL2이면 L2 거리(혹은 그 제곱)를 반환 → **범위**: [0, ∞).  
        - 만약 IndexFlatIP(내적) 등을 쓴다면 값 범위가 달라질 수 있음(음수가 될 수도 있음).
        """)

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

    # 인덱스 전체 문서 개수
    faiss_index_size = vectorstore.index.ntotal

    # 검색어 입력
    query = st.text_input("검색어를 입력하세요:")

    # 검색 실행
    if st.button("검색 실행") or query:
        if query.strip():
            try:
                # 전체 문서 검색 + 점수 반환
                docs_with_score = vectorstore.similarity_search_with_score(query, k=faiss_index_size)

                st.write(f"**검색 질의:** {query}")
                st.write(f"**검색 결과:** 전체 {faiss_index_size}개 중 {len(docs_with_score)}개")

                # 쿼리 임베딩 (코사인 유사도, L2 거리 직접 계산용)
                query_emb = embedding_model.embed_documents([query])
                query_emb = np.array(query_emb)  # shape (1, D)

                # 테이블 데이터 구성
                rows = []
                for doc, faiss_score in docs_with_score:
                    doc_emb = embedding_model.embed_documents([doc.page_content])
                    doc_emb = np.array(doc_emb)  # shape (1, D)

                    # L2 거리 = norm(doc_emb - query_emb)
                    l2_dist = np.linalg.norm(doc_emb - query_emb)

                    # 코사인 유사도
                    cos_sim = cosine_similarity(doc_emb, query_emb).flatten()[0]

                    rows.append({
                        "l2_distance": l2_dist,
                        "cosine_sim": cos_sim,
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        # 만약 FAISS score 컬럼도 보고싶으면 주석 해제:
                        # "faiss_score": faiss_score,
                    })

                df = pd.DataFrame(rows)
                st.dataframe(df)

                # XLSX 다운로드 버튼 추가
                # --------------------------------
                # 1) 파일명 = 검색어 + "_upstage_layout.xlsx"
                download_filename = f"{query}_upstage_layout.xlsx"

                # 2) 엑셀 최상단(첫 번째 행)에 검색어를 기록하기 위해:
                #    - df를 startrow=1에 쓰고, (row=0) 위치에는 "검색어: {query}"를 작성
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    # 먼저 df를 2번째 행부터(startrow=1)에 출력
                    df.to_excel(writer, index=False, sheet_name="SearchResults", startrow=1)
                    
                    # worksheet 객체 얻어오기
                    worksheet = writer.sheets["SearchResults"]
                    # 첫번째 행(0행), 0열에 검색어 기재
                    worksheet.write(0, 0, f"검색어:")
                    worksheet.write(0, 1, f"{query}")

                st.download_button(
                    label="Download results as XLSX",
                    data=buffer.getvalue(),
                    file_name=download_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                # --------------------------------
                
                # 시각화 (2D/3D)
                contents_list = df["content"].tolist()
                doc_embeddings_list = embedding_model.embed_documents(contents_list)
                doc_embeddings = np.array(doc_embeddings_list)

                tab2d, tab3d = st.tabs(["2D 시각화", "3D 시각화"])
                with tab2d:
                    fig_2d = visualize_embeddings_2d(
                        embeddings_array=doc_embeddings,
                        texts=contents_list,
                        query_text=query,
                        query_embedding=query_emb
                    )
                    st.plotly_chart(fig_2d, use_container_width=True)

                with tab3d:
                    fig_3d = visualize_embeddings_3d(
                        embeddings_array=doc_embeddings,
                        texts=contents_list,
                        query_text=query,
                        query_embedding=query_emb
                    )
                    st.plotly_chart(fig_3d, use_container_width=True)

            except Exception as e:
                st.error(f"검색 중 오류가 발생했습니다: {str(e)}")
        else:
            st.warning("검색어를 입력해주세요.")


if __name__ == "__main__":
    main()
