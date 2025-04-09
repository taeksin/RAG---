from langchain.embeddings.base import Embeddings
from upstage_embedding import get_upstage_embedding
from openai_embedding import get_openai_embedding
import streamlit as st

class CustomEmbeddings(Embeddings):
    """
    CustomEmbeddings 클래스는 선택한 임베딩 모델에 따라 쿼리 및 문서 임베딩을 생성합니다.
    
    Attributes:
        selected_embedding (str): 사용할 임베딩 모델 식별자 ("upstage_passage" 또는 "openai_small").
    """
    def __init__(self, selected_embedding: str):
        """
        CustomEmbeddings 객체를 초기화합니다.
        
        Args:
            selected_embedding (str): 사용할 임베딩 모델을 지정하는 문자열.
        """
        self.selected_embedding = selected_embedding

    def embed_query(self, text: str):
        """
        주어진 텍스트에 대해 선택된 임베딩 모델을 이용해 쿼리 임베딩을 생성합니다.
        
        Args:
            text (str): 임베딩할 쿼리 텍스트.
        
        Returns:
            list[float]: 입력 텍스트의 임베딩 결과 벡터, 실패 시 None.
        """
        if self.selected_embedding == "upstage_passage":
            # upstage 임베딩 API 사용 (모델: "passage")
            embedding = get_upstage_embedding(text, "passage")
            if embedding is None:
                st.error("쿼리 임베딩 생성 실패")
            return embedding
        elif self.selected_embedding == "openai_small":
            # OpenAI 임베딩 API 사용 (모델: "small")
            embedding = get_openai_embedding(text, "small")
            if embedding is None:
                st.error("쿼리 임베딩 생성 실패")
            return embedding

    def embed_documents(self, texts: list[str]):
        """
        주어진 여러 텍스트 문서에 대해 각각 임베딩을 생성합니다.
        
        Args:
            texts (list[str]): 문서 텍스트 리스트.
        
        Returns:
            list[list[float]]: 각 문서에 대한 임베딩 벡터 리스트.
        """
        return [self.embed_query(text) for text in texts]

if __name__ == "__main__":
    # 간단한 테스트: 선택한 임베딩 모델로 임베딩 생성 확인
    sample_text = "테스트 임베딩입니다."
    selected = "openai_small"  # 또는 "upstage_passage"
    custom_emb = CustomEmbeddings(selected)
    embedding = custom_emb.embed_query(sample_text)
    print(f"임베딩 결과 ({selected}):", embedding)
