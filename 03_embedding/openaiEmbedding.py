import os
import json
import pandas as pd
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_file(file, sheets, embedding_model, model):
    documents = []
    for sheet in sheets:
        try:
            df = pd.read_excel(file, engine='openpyxl', sheet_name=sheet)
        except Exception as e:
            print(f"시트 {sheet} 읽기 실패: {e}")
            continue

        # 'content', 'metadata' 컬럼 확인
        if "content" not in df.columns or "metadata" not in df.columns:
            print(f"파일 {file}의 시트 {sheet}에 'content' 또는 'metadata' 컬럼이 없습니다.")
            continue

        df = df.dropna(subset=["content", "metadata"])
        for index, row in df.iterrows():
            if pd.isna(row["content"]) or pd.isna(row["metadata"]):
                continue
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
            for pattern in ["[[[[[[이전청크]", "[[[[[[현재청크]", "[[[[[[다음청크]",
                            "[[[[[[현재페이지 전체내용]", "[[[[[[이전페이지 마지막 청크]", "[[[[[[다음페이지 첫번째 청크]"]:
                metadata["text"] = metadata["text"].replace(pattern, "")
            documents.append(Document(page_content=content, metadata=metadata))

    if not documents:
        print(f"파일 {file}에서 처리할 문서가 없습니다.")
        return None

    # 각 Excel 파일별로 벡터스토어 생성
    vectorstore = FAISS.from_documents(documents=documents, embedding=embedding_model)
    # 엑셀 파일명(확장자 제거) 사용하여 저장 폴더 지정
    excel_filename = os.path.splitext(os.path.basename(file))[0]
    save_path = os.path.join("vdb", "openai_small", f"{excel_filename}_{model}")
    vectorstore.save_local(save_path)
    print(f"║   -> {excel_filename} 파일의 임베딩이 성공적으로 저장되었습니다.")
    return save_path

def openaiEmbedding(folder_path):
    """
    folder_path 내부에 있는 모든 Excel 파일(.xlsx)을 개별로 처리하여
    OpenAI 임베딩 벡터스토어를 생성합니다.
    각 Excel 파일의 모든 시트를 사용하며, 파일별로 별도의 벡터스토어 폴더를 생성합니다.
    폴더 이름은 {엑셀파일명}_text-embedding-3-small 형식입니다.
    병렬처리를 사용하여 임베딩 시간을 단축합니다.
    """
    load_dotenv()

    # OpenAI API 설정
    api_key = os.getenv("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = api_key

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

    # 사용할 모델명 및 임베딩 모델 생성
    model = "text-embedding-3-small"
    embedding_model = OpenAIEmbeddings(model=model)

    # 각 Excel 파일별로 병렬 처리 시작
    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_file, file, sheets, embedding_model, model): file for file, sheets in excel_files}
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                results.append(result)
    return results

if __name__ == "__main__":
    folder_path = r"C:\Users\yoyo2\fas\RAG_Pre_processing\data\250331-16-57_모니터1p"
    openaiEmbedding(folder_path)
