import os
import numpy as np
import pandas as pd
import faiss
import json
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from openai import OpenAI  # Upstage API 사용

# Upstage API를 사용하여 벡터 생성하는 함수 (변경 없음)
def get_upstage_embedding(texts, client, model):
    """
    Upstage API를 사용하여 벡터 생성 (batch_size=100)
    """
    embeddings = []
    batch_size = 100  # Upstage API 최대 요청 개수
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        try:
            response = client.embeddings.create(
                model=model,
                input=batch_texts
            )
            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)
        except Exception as e:
            print(f"🚨 임베딩 요청 실패: {str(e)}")
    return embeddings

# UpstageEmbeddings 클래스 (Embeddings 객체 구현)
from langchain.embeddings.base import Embeddings

class UpstageEmbeddings(Embeddings):
    def __init__(self, client, model):
        self.client = client
        self.model = model

    def embed_documents(self, texts):
        return get_upstage_embedding(texts, self.client, self.model)

    def embed_query(self, text):
        return self.embed_documents([text])[0]

def upstageEmbedding(folder_path):
    """
    folder_path 내부에 있는 모든 Excel 파일(.xlsx)을 개별로 처리하여
    Upstage API를 사용한 임베딩 벡터스토어를 생성합니다.
    각 Excel 파일의 모든 시트를 사용하며, 파일별로 별도의 벡터스토어가 생성됩니다.
    """
    load_dotenv()

    # Upstage API 키 설정
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        print("UPSTAGE_API_KEY가 .env 파일에 설정되어 있지 않습니다.")
        return

    # Upstage API 클라이언트 초기화
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.upstage.ai/v1/solar"
    )

    # folder_path 내의 모든 Excel 파일 찾기
    excel_files = []
    for f in os.listdir(folder_path):
        if f.lower().endswith('.xlsx'):
            file_path = os.path.join(folder_path, f)
            try:
                xl = pd.ExcelFile(file_path, engine='openpyxl')
                sheets = xl.sheet_names
                excel_files.append((file_path, sheets))
            except Exception as e:
                print(f"Excel 파일 {f} 읽기 실패: {e}")

    if not excel_files:
        print("처리할 Excel 파일이 없습니다.")
        return

    # 폴더 내 각 Excel 파일별로 개별 벡터스토어 생성
    for file, sheets in excel_files:
        file_documents = []
        for sheet in sheets:
            try:
                df = pd.read_excel(file, engine='openpyxl', sheet_name=sheet)
            except Exception as e:
                print(f"시트 {sheet} 읽기 실패: {e}")
                continue

            if "content" not in df.columns or "metadata" not in df.columns:
                print(f"파일 {file}의 시트 {sheet}에 'content' 또는 'metadata' 컬럼이 없습니다.")
                continue

            df = df.dropna(subset=["content", "metadata"])
            for _, row in df.iterrows():
                content = row["content"]
                for pattern in ["[[[[[[이전청크]", "[[[[[[현재청크]", "[[[[[[다음청크]",
                                "[[[[[[현재페이지 전체내용]", "[[[[[[이전페이지 마지막 청크]", "[[[[[[다음페이지 첫번째 청크]"]:
                    content = content.replace(pattern, "")
                try:
                    metadata = json.loads(row["metadata"])
                except Exception as e:
                    print(f"메타데이터 파싱 실패 (파일 {file}, 시트 {sheet}): {e}")
                    continue
                for pattern in ["[[[[[[이전청크]", "[[[[[[현재청크]", "[[[[[[다음청크]",
                                "[[[[[[현재페이지 전체내용]", "[[[[[[이전페이지 마지막 청크]", "[[[[[[다음페이지 첫번째 청크]"]:
                    metadata["text"] = metadata["text"].replace(pattern, "")
                file_documents.append(Document(page_content=content, metadata=metadata))
        
        if not file_documents:
            print(f"파일 {file}에서 처리할 문서가 없습니다.")
            continue

        file_text_contents = [doc.page_content for doc in file_documents]
        file_embeddings = get_upstage_embedding(file_text_contents, client, "embedding-passage")
        if len(file_embeddings) != len(file_documents):
            print("🚨 임베딩 개수가 문서 개수와 일치하지 않습니다.")
            continue

        dimension = len(file_embeddings[0])
        file_index = faiss.IndexFlatL2(dimension)
        # pylint: disable=no-value-for-parameter
        file_index.add(np.array(file_embeddings, dtype=np.float32))

        file_index_to_docstore_id = {i: str(i) for i in range(len(file_documents))}
        file_docstore = {str(i): doc for i, doc in enumerate(file_documents)}

        upstage_embedding_obj = UpstageEmbeddings(client, "embedding-passage")
        file_vectorstore = FAISS(
            embedding_function=upstage_embedding_obj,
            index=file_index,
            docstore=file_docstore,
            index_to_docstore_id=file_index_to_docstore_id
        )

        # 엑셀 파일명(확장자 제거) 사용하여 저장 폴더 지정
        excel_filename = os.path.splitext(os.path.basename(file))[0]
        save_path = f"vdb/upstage_faiss/{excel_filename}_embedding-passage/"
        file_vectorstore.save_local(save_path)
        print(f"║   -> {excel_filename} 파일의 임베딩이 성공적으로 저장되었습니다.")
        # print(f"✅ FAISS 벡터 개수: {file_vectorstore.index.ntotal}")
        # print(f"✅ 저장된 문서 개수: {len(file_vectorstore.docstore)}")

if __name__ == "__main__":
    folder_path = r"C:\Users\yoyo2\fas\RAG_Pre_processing\data\250331-16-57_모니터1p"
    upstageEmbedding(folder_path)
