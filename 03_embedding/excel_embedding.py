import os
import json
import pandas as pd
from langchain.schema import Document
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from tqdm import tqdm  # tqdm 임포트

def embedding_xl_to_faiss(excel_paths):
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY가 .env 파일에 설정되어 있지 않습니다.")
    
    # 내부 매핑 정보 설정
    mapping = {
        "01": "01_upstageLayout",
        "02": "02_upstageLayout_overlap_1",
        "03": "03_upstageLayout_overlap_2",
        "04": "04_Nsplit"
    }
    
    # 전달받은 excel_paths 리스트에 대해 반복
    for excel_path in excel_paths:
        df = pd.read_excel(excel_path)
        documents = []
        # tqdm을 사용하여 각 행을 처리하는 진행 상황 표시
        for _, row in tqdm(df.iterrows(), total=len(df), desc=f"║ Processing {os.path.basename(excel_path)}"):
            try:
                metadata = json.loads(str(row["metadata"]))
            except Exception as e:
                # print(f"[경고] metadata 파싱 실패: {e}")
                metadata = {}
            
            # page_content를 강제로 문자열로 변환
            page_content = row["page_content"]
            # 만약 page_content가 숫자 0이라면, 명시적으로 "0"이라는 문자열로 변환되게 함
            if not isinstance(page_content, str):
                page_content = str(page_content)
            
            doc = Document(page_content=page_content, metadata=metadata)
            documents.append(doc)

        
        embedding_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=openai_api_key
        )
        
        vectorstore = FAISS.from_documents(
            documents=documents,
            embedding=embedding_model
        )
        
        # 엑셀 파일 이름에서 두 자리 코드 추출 (예: "all_01.xlsx" → "01")
        basename = os.path.basename(excel_path)
        try:
            two_digit = basename.split("_")[1].split(".")[0]
        except IndexError:
            two_digit = "00"
        folder_name = mapping.get(two_digit, "00_unknown")
        
        # FAISS DB 저장 경로 구성 (예: vdb/faiss_index/small/01_upstageLayout)
        faiss_save_path = os.path.join("vdb", "faiss_index", "small", folder_name)
        os.makedirs(faiss_save_path, exist_ok=True)
        
        vectorstore.save_local(faiss_save_path)
        print(f"║ [임베딩 완료] {excel_path} -> FAISS 저장 경로: {faiss_save_path}")

if __name__ == "__main__":
    DATA_DIR = r"C:\Users\yoyo2\fas\RAG_Pre_processing\data"
    excel_files = [
        os.path.join(DATA_DIR, "all_01.xlsx"),
        os.path.join(DATA_DIR, "all_02.xlsx"),
        os.path.join(DATA_DIR, "all_03.xlsx"),
        os.path.join(DATA_DIR, "all_04.xlsx")
    ]
    
    embedding_xl_to_faiss(excel_files)
