import streamlit as st
import os
import numpy as np
import pandas as pd
import io
import json
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai.embeddings import OpenAIEmbeddings

from sklearn.decomposition import PCA
import plotly.express as px
import plotly.graph_objects as go
from sklearn.metrics.pairwise import cosine_similarity

# -----------------------------
# db_options.json 파일에서 DB 옵션 불러오기
# -----------------------------
def load_db_options(filepath="db_options.json"):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

# -----------------------------
# 시각화 함수들 (2D/3D)
# -----------------------------
def visualize_embeddings_2d(embeddings_array, texts, query_text=None, query_embedding=None):
    pca = PCA(n_components=2)
    reduced = pca.fit_transform(embeddings_array)
    df = pd.DataFrame(reduced, columns=["X축", "Y축"])
    df["text"] = [t[:15] for t in texts]

    fig = px.scatter(
        df,
        x="X축",
        y="Y축",
        text="text",
        title="검색 결과 임베딩 2D 시각화 (PCA)"
    )
    fig.update_traces(textposition="top center", marker=dict(size=6))

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
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("ERROR: OPENAI_API_KEY가 설정되어 있지 않습니다.")
        return

    # 사이드바: DB 선택 및 설명
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
                    ---
                    **시각화**
                    - 각 점은 원본 텍스트의 앞 15글자를 표시합니다.
                    - 2D와 3D를 지원합니다 탭을 바꿔서 확인 하실 수 있습니다.
                    """)
        
    # db_options.json 파일에서 DB 옵션 불러오기
    db_options = load_db_options("04_search/db_options.json")

    # 상단 제목
    st.title("RAG 임베딩과정 선택지 비교")
    
    # 세부 안내
    st.write("**아래 각 3단계에서 원하는 옵션을 선택하세요**")
    st.write("---")

    # --- CSS를 이용한 세로 구분선 스타일 ---
    st.markdown(
        """
        <style>
        .vertical-line {
            display: inline-block;
            border-left: 1px solid #888;
            margin: 0 1rem;
            /* 세로선 길이 늘리기 */
            height: 3.2em; 
            vertical-align: middle;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 라디오 버튼을 가로로 배치 (세로 구분선 포함)
    col1, col2, col3, col4, col5 = st.columns([2.1, 0.2, 3, 0.2, 3])

    with col1:
        st.markdown("##### 임베딩모델")
        selected_category = st.radio(
            "***임베딩모델을 선택합니다***",
            options=list(db_options.keys()),
            horizontal=True,
            key="db_category"
        )
    with col2:
        st.markdown('<div class="vertical-line"></div>', unsafe_allow_html=True)
    with col3:
        st.markdown("##### Content 구성 선택")
        selected_content = st.radio(
            "***Content 구성을 선택합니다***",
            options=list(db_options[selected_category].keys()),
            horizontal=True,
            key="db_content"
        )
    with col4:
        st.markdown('<div class="vertical-line"></div>', unsafe_allow_html=True)
    with col5:
        st.markdown("##### Metadata 구성 선택")
        description_options = list(db_options[selected_category][selected_content].keys())
        selected_description = st.radio(
            "***Metadata 구성을 선택합니다***",
            options=description_options,
            horizontal=True,
            key="db_desc"
        )

    st.write("---")

    # 선택된 항목에 따른 최종 정보 업데이트
    final_info = db_options[selected_category][selected_content][selected_description]
    vdb_index_path = final_info["path"]
    base_description = final_info["description"]

    # 결과 표시
    st.write(f"**사용 할 VectorDB Path**: `{vdb_index_path}`")

    # 임베딩 모델 생성
    embedding_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=api_key
    )

    # FAISS 인덱스 로드
    try:
        vectorstore = FAISS.load_local(
            folder_path=vdb_index_path,
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
                # 전체 문서 개수만큼 검색
                docs_with_score = vectorstore.similarity_search_with_score(query, k=faiss_index_size)
                st.write(f"**검색 질의:** {query}")
                st.write(f"**검색 결과:** 전체 {faiss_index_size}개 중 {len(docs_with_score)}개")

                # 쿼리와 문서를 임베딩
                query_emb = embedding_model.embed_documents([query])[0]
                query_emb = np.array(query_emb)

                contents_list = [doc.page_content for doc, _ in docs_with_score]
                doc_embeddings = embedding_model.embed_documents(contents_list)
                doc_embeddings = np.array(doc_embeddings)

                # L2 거리와 코사인 유사도
                l2_dists = np.linalg.norm(doc_embeddings - query_emb, axis=1)
                cos_sims = cosine_similarity(doc_embeddings, query_emb.reshape(1, -1)).flatten()

                # 결과 표
                rows = []
                for i, (doc, _) in enumerate(docs_with_score):
                    rows.append({
                        "l2_distance": l2_dists[i],
                        "cosine_sim": cos_sims[i],
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                    })
                df = pd.DataFrame(rows)
                st.dataframe(df)

                # XLSX 다운로드
                download_filename = f"{query}_upstage_layout.xlsx"
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name="SearchResults", startrow=1)
                    worksheet = writer.sheets["SearchResults"]
                    worksheet.write(0, 0, "검색어:")
                    worksheet.write(0, 1, query)
                st.download_button(
                    label="Download results as XLSX",
                    data=buffer.getvalue(),
                    file_name=download_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                # 2D / 3D 시각화 탭
                tab2d, tab3d = st.tabs(["2D 시각화", "3D 시각화"])
                with tab2d:
                    fig_2d = visualize_embeddings_2d(
                        embeddings_array=doc_embeddings,
                        texts=contents_list,
                        query_text=query,
                        query_embedding=query_emb.reshape(1, -1)
                    )
                    st.plotly_chart(fig_2d, use_container_width=True)
                with tab3d:
                    fig_3d = visualize_embeddings_3d(
                        embeddings_array=doc_embeddings,
                        texts=contents_list,
                        query_text=query,
                        query_embedding=query_emb.reshape(1, -1)
                    )
                    st.plotly_chart(fig_3d, use_container_width=True)

            except Exception as e:
                st.error(f"검색 중 오류가 발생했습니다: {str(e)}")
        else:
            st.warning("검색어를 입력해주세요.")

if __name__ == "__main__":
    main()
