import os
import time
import numpy as np
import pandas as pd
import faiss
import json
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from openai import OpenAI  # Upstage API 사용
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_TOKENS = 4000  # 최대 문자 수 기준

def split_text_into_chunks_by_chars(text, max_length=MAX_TOKENS):
    """
    텍스트를 문자 단위로 분할하여, 최대 max_length 이하의 청크 리스트를 반환합니다.
    """
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

def get_embedding_dimension(client, model):
    """
    짧은 텍스트("test")를 사용하여 임베딩 차원을 확인합니다.
    """
    try:
        response = client.embeddings.create(model=model, input=["test"])
        return len(response.data[0].embedding)
    except Exception as e:
        print(f"🚨 임베딩 차원 확인 실패: {str(e)}")
        return None

def get_embedding_for_text(text, client, model, dim, max_retries=3):
    """
    개별 텍스트(text)에 대해 임베딩 API를 호출합니다.
    텍스트 길이가 MAX_TOKENS(문자 수 기준)보다 길면 청크로 분할 후 각 청크 임베딩의 평균을 반환합니다.
    실패 시 max_retries 만큼 재시도하며, 모두 실패하면 0 벡터를 반환합니다.
    """
    def call_embedding(input_text):
        for attempt in range(max_retries):
            try:
                response = client.embeddings.create(model=model, input=[input_text])
                return response.data[0].embedding
            except Exception as e:
                error_str = str(e)
                # print(f"🚨 임베딩 요청 실패 (개별 처리, 시도 {attempt+1}): {error_str}")
                # 429 오류이면 지정한 대기 시간 적용
                if '429' in error_str:
                    if attempt == 0:
                        delay = 9  # 3²=9초
                    elif attempt == 1:
                        delay = 20  # 3³=27초
                    else:
                        delay = 30
                    time.sleep(delay)
                else:
                    time.sleep(1)
        return None

    # 텍스트 길이가 MAX_TOKENS보다 크면 청크로 분할 후 각 청크 임베딩을 병렬(동시 실행 최대 2개)로 요청
    if len(text) > MAX_TOKENS:
        chunks = split_text_into_chunks_by_chars(text, MAX_TOKENS)
        sub_embeddings = []
        with ThreadPoolExecutor(max_workers=min(len(chunks), 2)) as executor:
            futures = [executor.submit(call_embedding, chunk) for chunk in chunks]
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    sub_embeddings.append(result)
        if sub_embeddings:
            avg_embedding = np.mean(np.array(sub_embeddings), axis=0).tolist()
            return avg_embedding
        else:
            return [0.0] * dim
    else:
        emb = call_embedding(text)
        return emb if emb is not None else [0.0] * dim

def get_upstage_embedding_parallel(texts, client, model, dim, max_workers=2):
    """
    texts: 문서별 텍스트 리스트 (각 행 단위)
    각 텍스트에 대해 get_embedding_for_text()를 동시 실행 최대 max_workers 개로 호출하여 임베딩을 생성합니다.
    """
    embeddings = [None] * len(texts)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {executor.submit(get_embedding_for_text, text, client, model, dim): idx for idx, text in enumerate(texts)}
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                embeddings[idx] = future.result()
            except Exception as e:
                print(f"🚨 임베딩 처리 중 에러 (인덱스 {idx}): {str(e)}")
                embeddings[idx] = [0.0] * dim
    return embeddings

# UpstageEmbeddings 클래스 (Embeddings 객체 구현)
from langchain.embeddings.base import Embeddings

class UpstageEmbeddings(Embeddings):
    def __init__(self, client, model, dim):
        self.client = client
        self.model = model
        self.dim = dim

    def embed_documents(self, texts):
        return get_upstage_embedding_parallel(texts, self.client, self.model, self.dim, max_workers=2)

    def embed_query(self, text):
        return self.embed_documents([text])[0]

def upstageEmbedding(folder_path):
    """
    folder_path 내부에 있는 모든 Excel 파일(.xlsx)을 개별로 처리하여
    Upstage API를 사용한 임베딩 벡터스토어를 생성합니다.
    각 Excel 파일의 모든 시트를 사용하며, 파일별로 별도의 벡터스토어가 생성됩니다.
    파일 간 내용이 섞이지 않도록 처리하며, 문서별 임베딩 요청은 동시 실행 최대 2개로 제한됩니다.
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

    # 임베딩 차원 확인
    dim = get_embedding_dimension(client, "embedding-passage")
    if dim is None:
        print("임베딩 차원을 확인할 수 없습니다. 종료합니다.")
        return

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

    # 각 Excel 파일별로 문서(Document) 리스트 생성 및 임베딩 처리 (행 단위)
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
            for index, row in df.iterrows():
                content = row["content"]
                # 불필요한 패턴 제거
                for pattern in ["[[[[[[이전청크]", "[[[[[[현재청크]", "[[[[[[다음청크]",
                                "[[[[[[현재페이지 전체내용]", "[[[[[[이전페이지 마지막 청크]", "[[[[[[다음페이지 첫번째 청크]"]:
                    content = content.replace(pattern, "")
                try:
                    metadata = json.loads(row["metadata"])
                except Exception as e:
                    print(f"메타데이터 파싱 실패 (파일 {file}, 시트 {sheet}, 행 {index}): {e}")
                    continue
                if "text" in metadata:
                    for pattern in ["[[[[[[이전청크]", "[[[[[[현재청크]", "[[[[[[다음청크]",
                                    "[[[[[[현재페이지 전체내용]", "[[[[[[이전페이지 마지막 청크]", "[[[[[[다음페이지 첫번째 청크]"]:
                        metadata["text"] = metadata["text"].replace(pattern, "")
                file_documents.append(Document(page_content=content, metadata=metadata))
        
        if not file_documents:
            print(f"파일 {file}에서 처리할 문서가 없습니다.")
            continue

        # 각 Excel 파일 내 각 행(문서)에 대해 동시 실행 최대 2개로 임베딩 요청
        file_text_contents = [doc.page_content for doc in file_documents]
        file_embeddings = get_upstage_embedding_parallel(file_text_contents, client, "embedding-passage", dim, max_workers=2)
        if len(file_embeddings) != len(file_documents):
            print("🚨 임베딩 개수가 문서 개수와 일치하지 않습니다.")
            continue

        # FAISS 인덱스 생성
        file_index = faiss.IndexFlatL2(dim)
        try:
            file_index.add(np.array(file_embeddings, dtype=np.float32))
        except Exception as e:
            print(f"FAISS 인덱스 추가 실패: {e}")
            continue

        file_index_to_docstore_id = {i: str(i) for i in range(len(file_documents))}
        file_docstore = {str(i): doc for i, doc in enumerate(file_documents)}

        upstage_embedding_obj = UpstageEmbeddings(client, "embedding-passage", dim)
        file_vectorstore = FAISS(
            embedding_function=upstage_embedding_obj,
            index=file_index,
            docstore=file_docstore,
            index_to_docstore_id=file_index_to_docstore_id
        )

        excel_filename = os.path.splitext(os.path.basename(file))[0]
        save_path = os.path.join("vdb", "upstage_passage", f"{excel_filename}_embedding-passage")
        file_vectorstore.save_local(save_path)
        print(f"║   -> {excel_filename} 파일의 임베딩이 성공적으로 저장되었습니다.")

if __name__ == "__main__":
    folder_path = r"C:\Users\yoyo2\fas\RAG_Pre_processing\data\250331-16-57_모니터1p"
    print("║ ✅ upstageEmbedding 시작")
    upstageEmbedding(folder_path)
