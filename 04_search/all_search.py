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
# DB 옵션 설정 (DB 1~4)
# -----------------------------
db_options = {
    "DB 1": {
        "path": "vdb/faiss_index/small/01_upstageLayout",
        "description": "upstage에서 나눠준 그대로 layout사용"
    },
    "DB 2": {
        "path": "vdb/faiss_index/small/02_upstageLayout_overlap_1",
        "description": "upstageLayout에 직전 블록까지만 overlap"
    },
    "DB 3": {
        "path": "vdb/faiss_index/small/03_upstageLayout_overlap_2",
        "description": "upstageLayout에 overlap만큼 채워질 때 까지 이전 내용 가져옴"
    },
    "DB 4": {
        "path": "vdb/faiss_index/small/04_Nsplit",
        "description": "그냥 텍스트에서 Chunk(500), Overlap(100)"
    }
}

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
        st.header("DB 선택")
        selected_db = st.radio(
            "사용할 DB를 선택하세요:",
            options=list(db_options.keys()),
            format_func=lambda x: f"{x} - {db_options[x]['description']}"
        )
        st.markdown(f"**선택된 DB:** {selected_db}\n**경로:** `{db_options[selected_db]['path']}`")
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
                
    # 선택된 DB에 따른 vdb 경로 설정
    vdb_index_path = db_options[selected_db]["path"]

    # 선택된 DB의 description을 사용하여 메인 타이틀 변경
    st.title(db_options[selected_db]["description"])

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
                # FAISS에서 모든 문서를 검색 (전체 개수를 k로 전달)
                docs_with_score = vectorstore.similarity_search_with_score(query, k=faiss_index_size)
                st.write(f"**검색 질의:** {query}")
                st.write(f"**검색 결과:** 전체 {faiss_index_size}개 중 {len(docs_with_score)}개")

                # 배치 임베딩: 쿼리와 문서들을 한 번에 임베딩
                query_emb = embedding_model.embed_documents([query])[0]
                query_emb = np.array(query_emb)  # shape (D,)
                
                # 모든 검색 결과의 문서 내용을 리스트로 추출
                contents = [doc.page_content for doc, _ in docs_with_score]
                doc_embeddings = embedding_model.embed_documents(contents)
                doc_embeddings = np.array(doc_embeddings)  # shape (n, D)
                
                # 벡터 연산을 이용해 L2 거리와 코사인 유사도 계산
                l2_dists = np.linalg.norm(doc_embeddings - query_emb, axis=1)
                cos_sims = cosine_similarity(doc_embeddings, query_emb.reshape(1, -1)).flatten()
                
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

                # XLSX 다운로드 버튼
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

                contents_list = df["content"].tolist()
                doc_embeddings = embedding_model.embed_documents(contents_list)
                doc_embeddings = np.array(doc_embeddings)

                # tab2d, tab3d = st.tabs(["2D 시각화", "3D 시각화"])
                # with tab2d:
                #     fig_2d = visualize_embeddings_2d(
                #         embeddings_array=doc_embeddings,
                #         texts=contents_list,
                #         query_text=query,
                #         query_embedding=query_emb.reshape(1, -1)
                #     )
                #     st.plotly_chart(fig_2d, use_container_width=True)
                # with tab3d:
                #     fig_3d = visualize_embeddings_3d(
                #         embeddings_array=doc_embeddings,
                #         texts=contents_list,
                #         query_text=query,
                #         query_embedding=query_emb.reshape(1, -1)
                #     )
                #     st.plotly_chart(fig_3d, use_container_width=True)
            except Exception as e:
                st.error(f"검색 중 오류가 발생했습니다: {str(e)}")
        else:
            st.warning("검색어를 입력해주세요.")

if __name__ == "__main__":
    main()
