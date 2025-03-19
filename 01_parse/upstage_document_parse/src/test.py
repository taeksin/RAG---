from langchain.text_splitter import RecursiveCharacterTextSplitter

def split_text_with_recursive_splitter(text):
    chunk_size=500
    chunk_overlap=100
    
    # RecursiveCharacterTextSplitter를 이용한 텍스트 분할
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_text(text)
    
    return chunks

# 테스트 예제
text = """

"""
chunks = split_text_with_recursive_splitter(text)

# 분할된 결과 출력
for i, chunk in enumerate(chunks):
    print(f"\n{'-'*50}\n{chunk}\n")
