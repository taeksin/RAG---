import os
from dotenv import load_dotenv
from openai import OpenAI  # pip install openai (openai==1.52.2)

def get_upstage_embedding(text, model):
    """
    주어진 텍스트(text)와 모델 파라미터(model)를 기반으로
    Upstage 임베딩 API를 사용하여 임베딩 벡터를 생성하는 함수입니다.
    
    매개변수:
        text (str): 임베딩 생성을 원하는 입력 텍스트.
        model (str): "passage" 또는 "query" 값으로, 사용할 모델을 지정.
    
    반환값:
        임베딩 벡터 (list[float]) 또는 임베딩 생성 실패 시 None.
    """
    load_dotenv()  # .env 파일 로드
    
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        raise ValueError("ERROR: UPSTAGE_API_KEY가 .env 파일에 설정되어 있지 않습니다.")
    
    # 모델 파라미터에 따른 실제 모델 이름 매핑
    
    # Upstage API 클라이언트 초기화 (base_url은 제공된 코드 기준 사용)
    client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1/solar")
    
    try:
        response = client.embeddings.create(
            input=text,
            model=f"embedding-{model}"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"임베딩 요청 실패: {e}")
        return None

if __name__ == "__main__":
    sample_text = "Solar embeddings are awesome"
    model = "passage"
    embedding_passage = get_upstage_embedding(sample_text, model)
    print(f"{model} 임베딩 결과:")
    print(embedding_passage)
    