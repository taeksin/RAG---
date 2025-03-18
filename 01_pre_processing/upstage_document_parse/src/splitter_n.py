import os
from langchain.text_splitter import RecursiveCharacterTextSplitter

def split_markdown_file(file_path):
    """
    Markdown 파일 전체를 읽어, 
    (옵션에 따라) <<BLOCKEND>>와 "elementId:"로 시작하는 줄들을 제거한 후,
    RecursiveCharacterTextSplitter를 사용하여 chunk_size와 chunk_overlap 기준으로
    텍스트를 청크(분할된 텍스트) 리스트로 반환하는 함수.
    
    :param file_path: 원본 Markdown 파일 경로
    :param chunk_size: 각 청크의 최대 문자 수 (기본값 500)
    :param chunk_overlap: 인접 청크 간 중첩 문자 수 (기본값 100)
    :param remove_element_id: True이면 "elementId:"로 시작하는 줄들을 제거 (기본값 True)
    :return: 청크 리스트
    """
    chunk_size=500
    chunk_overlap=100
    remove_element_id=True
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    # 기존의 <<BLOCKEND>> 마커 모두 제거
    text = text.replace("<<BLOCKEND>>", "")
    
    # 옵션에 따라 "elementId:"로 시작하는 줄 제거
    if remove_element_id:
        lines = text.splitlines()
        text = "\n".join([line for line in lines if not line.strip().startswith("elementId:")])
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_text(text)
    return chunks

def process_folder(folder_path):
    """
    입력된 폴더 내에서 _converted.md로 끝나는 모든 파일을 찾아 분할 후,
    각 파일에 대해 _split.md 파일로 저장하는 함수.
    
    :param folder_path: 대상 폴더 경로
    :param remove_element_id: True이면 "elementId:"로 시작하는 줄들을 제거 (기본값 True)
    :param chunk_size: 각 청크의 최대 문자 수 (기본값 500)
    :param chunk_overlap: 인접 청크 간 중첩 문자 수 (기본값 100)
    :return: 파일별 청크 리스트 {파일경로: [청크, ...]}
    """
    md_files = [os.path.join(folder_path, f) 
                for f in os.listdir(folder_path) if f.endswith("_converted.md")]

    results = {}
    for file_path in md_files:
        print(f"Processing file: {file_path}")
        chunks = split_markdown_file(file_path)
        results[file_path] = chunks

        # _converted.md 파일을 _split.md 파일로 저장 (각 청크 뒤에 <<BLOCKEND>> 추가)
        output_file = file_path.replace("_converted.md", "_split.md")
        with open(output_file, "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(chunk + "\n\n<<BLOCKEND>>\n\n")
        print(f"  → {len(chunks)}개의 청크 생성됨. 저장: {output_file}")

    return results

if __name__ == "__main__":
    folder_path = "01_pre_processing/upstage_document_parse/temp/250314-14-42_20241220_[교재]_연말정산 세무_이석정_한국_회원_3.5시간65~68"
    process_folder(folder_path)
