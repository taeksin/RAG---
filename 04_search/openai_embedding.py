# openai_embedding.py
import os
from dotenv import load_dotenv
import numpy as np
from langchain_openai.embeddings import OpenAIEmbeddings

def get_openai_embedding(query: str, model: str):
    """
    주어진 query 문자열을 text-embedding-3-small 모델을 이용해 임베딩합니다.

    Parameters:
        query (str): 임베딩할 텍스트.
        openai_api_key (str): OpenAI API 키.

    Returns:
        np.ndarray: query의 임베딩 결과를 넘파이 배열로 반환.
    """
    
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
        
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다.")
    
    embedding_model = OpenAIEmbeddings(
        model=f"text-embedding-3-{model}",
        openai_api_key=openai_api_key
    )
    
    # 임베딩 결과는 리스트 형태이므로 첫 번째(유일한) 값을 선택 후 numpy 배열로 변환
    embedding = embedding_model.embed_documents([query])[0]
    return np.array(embedding)


if __name__ == "__main__":
    sample_text = "안녕하세요, 임베딩 테스트입니다."
    model = "small"
    embedding_result = get_openai_embedding(sample_text, model)
    print(f"{model} 임베딩 결과:", embedding_result)
