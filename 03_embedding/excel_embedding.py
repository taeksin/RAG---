import os
import json
import pandas as pd
from langchain.schema import Document
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

def embed_from_excel(excel_path, faiss_save_path):
    """
    Excel 파일에 저장된 데이터를 읽어와, 각 행을 Document로 변환한 후
    임베딩을 수행하여 FAISS 벡터스토어를 생성하고 저장합니다.
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("ERROR: OPENAI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")

    df = pd.read_excel(excel_path)
    documents = []
    for _, row in df.iterrows():
        try:
            metadata = json.loads(row["metadata"])
        except Exception as e:
            print(f"[경고] metadata 파싱 실패: {e}")
            metadata = {}
        doc = Document(page_content=row["page_content"], metadata=metadata)
        documents.append(doc)

    embedding_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=api_key
    )

    vectorstore = FAISS.from_documents(
        documents=documents,
        embedding=embedding_model
    )

    os.makedirs(faiss_save_path, exist_ok=True)
    vectorstore.save_local(faiss_save_path)

    print("\n[임베딩 결과]")
    print(f"엑셀 파일: {excel_path}")
    print(f" → FAISS 경로: {faiss_save_path}")

if __name__ == "__main__":
    excel_path = "data/all_documents.xlsx"
    faiss_save_path = os.path.join("vdb", "faiss_index", "small", "merged")
    embed_from_excel(excel_path, faiss_save_path)
