import os
import io
import numpy as np
import pandas as pd
from dotenv import load_dotenv
import streamlit as st

from config import load_db_options
from vectorsearch import load_vectorstore, search_query_vectorstore
from visualization import create_visualization_2d, create_visualization_3d

# .env 파일 로드
load_dotenv()

# DB 옵션 선택 인터페이스 (config.py 이용)
db_options = load_db_options("04_search/db_options.json")

# 상단 제목 및 설명
st.title("RAG 임베딩과정 선택지 비교")
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

# 선택한 벡터스토어 경로 표시
st.write(f"**사용 할 VectorDB Path**: `{vdb_index_path}`")
st.write(f"임베딩모델 | 임베딩한 내용(content)설명 | metadata구성")
st.write(f"{base_description}")

# FAISS 벡터스토어 로드 (vectorsearch.py 이용)
vectorstore = load_vectorstore(vdb_index_path, selected_category)

# 저장소에서 DB 문서와 임베딩 배열 추출
docs = vectorstore.docstore._dict if hasattr(vectorstore.docstore, '_dict') else vectorstore.docstore
db_texts = [doc.page_content for doc in docs.values()]
db_embeddings = vectorstore.index.reconstruct_n(0, vectorstore.index.ntotal)

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

# 검색 인터페이스
def main():
    st.header("검색")
    query = st.text_input("검색할 텍스트를 입력하세요:", placeholder="예: 관세", key="query")
    
    if st.button("검색 실행") and query:
        results, query_vector = search_query_vectorstore(query, selected_category, vectorstore, db_embeddings)
        if results:
            # 결과 컬럼 순서: L2 거리, 코사인 유사도, 텍스트, 메타데이터
            df_results = pd.DataFrame(results, columns=["L2 거리", "코사인 유사도", "텍스트", "메타데이터"])
            df_results = df_results.sort_values(by="코사인 유사도", ascending=False)
            st.subheader("검색 결과")
            st.write(f"**검색 질의:** {query}")
            st.write(f"**검색 결과:** 전체 {vectorstore.index.ntotal}개 중 {len(results)}개")
            st.dataframe(df_results.style.format({"L2 거리": "{:.4f}", "코사인 유사도": "{:.4f}"}))
            
            # XLSX 다운로드
            download_filename = f"{query}_{selected_category}.xlsx"
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_results.to_excel(writer, index=False, sheet_name="SearchResults", startrow=1)
                worksheet = writer.sheets["SearchResults"]
                worksheet.write(0, 0, "검색어:")
                worksheet.write(0, 1, query)
            st.download_button(
                label="Download results as XLSX",
                data=buffer.getvalue(),
                file_name=download_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            # 2D, 3D 시각화 탭 추가
            tab2d, tab3d = st.tabs(["2D 시각화", "3D 시각화"])
            with tab2d:
                fig2d = create_visualization_2d(db_embeddings, db_texts, query_embedding=query_vector.reshape(1, -1), query_text=query)
                st.plotly_chart(fig2d, use_container_width=True)
            with tab3d:
                fig3d = create_visualization_3d(db_embeddings, db_texts, query_embedding=query_vector.reshape(1, -1), query_text=query)
                st.plotly_chart(fig3d, use_container_width=True)
        else:
            st.warning("검색 결과가 없습니다.")

if __name__ == "__main__":
    main()
