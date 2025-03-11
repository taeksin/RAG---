import os
from dotenv import load_dotenv
from llama_cloud_services import LlamaParse
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

# .env에서 API 키 불러오기
load_dotenv()
llama_api_key = os.getenv("LLAMA_CLOUD_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

if not llama_api_key:
    raise ValueError("❌ LLAMA_CLOUD_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요!")
if not openai_api_key:
    raise ValueError("❌ OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요!")

# LlamaParse 설정 (Markdown 변환)
parser = LlamaParse(result_type="markdown", premium_mode=True)

# PDF 파일 경로
pdf_path = "pdf/모니터8p.pdf"

# PDF 문서 파싱 (Markdown으로 변환)
file_extractor = {".pdf": parser}
documents = SimpleDirectoryReader(input_files=[pdf_path], file_extractor=file_extractor).load_data()

# OpenAI LLM 및 Embeddings 설정
llm = OpenAI(api_key=openai_api_key)
embedding = OpenAIEmbedding(api_key=openai_api_key)

# 문서 인덱싱
index = VectorStoreIndex.from_documents(documents, llm=llm, embed_model=embedding)
query_engine = index.as_query_engine()

# 샘플 질의 수행
query = "이 문서의 주요 내용은 무엇인가요?"
response = query_engine.query(query)
print("🔍 질의 응답 결과:", response)
