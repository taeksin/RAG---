import os
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter

def split_markdown_file(file_path, chunk_size=500, chunk_overlap=100):
    """
    Markdown 파일을 `<<BLOCKEND>>` 단위로 분할하고, 
    각 블록을 유지하되 너무 긴 경우 내부적으로 추가 분할하는 함수.

    :param file_path: 원본 Markdown 파일 경로
    :param chunk_size: 각 청크의 최대 문자 수 (기본 500)
    :param chunk_overlap: 인접 청크 간 중첩 문자 수 (기본 100)
    :return: 블록 단위로 분할된 리스트
    """
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    # 1차 분할: `<<BLOCKEND>>` 기준으로 블록 분할
    blocks = text.split("<<BLOCKEND>>")
    final_chunks = []

    # 2차 분할: 블록 내부 추가 분할을 위한 splitter
    sub_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )

    for block in blocks:
        block = block.strip()  # 앞뒤 공백 제거
        
        if not block:
            continue  # 빈 블록 제거

        # **그림/표 포함 블록인지 체크**
        if "![](" in block:  
            final_chunks.append(block)  # 표/그림 포함 블록은 무조건 유지
        elif len(block) <= chunk_size:
            final_chunks.append(block)  # chunk_size 이하이면 그대로 추가
        else:
            # 너무 긴 블록은 내부적으로 추가 분할
            sub_chunks = sub_splitter.split_text(block)
            final_chunks.extend(sub_chunks)

    return final_chunks

def process_folder(folder_path, chunk_size=500, chunk_overlap=100):
    """
    입력된 폴더 내에서 `_converted.md`로 끝나는 모든 파일을 찾아 분할 후,
    각 파일에 대해 `_split.md` 파일로 저장하는 함수.

    :param folder_path: 대상 폴더 경로
    :return: 파일별 블록 리스트 {파일경로: [블록, ...]}
    """
    md_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith("_converted.md")]

    results = {}
    for file_path in md_files:
        print(f"Processing file: {file_path}")
        chunks = split_markdown_file(file_path, chunk_size, chunk_overlap)
        results[file_path] = chunks

        # `_split.md`로 저장
        output_file = file_path.replace("_converted.md", "_split.md")
        with open(output_file, "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(chunk + "\n\n<<SPLIT>>\n\n")
        print(f"  → {len(chunks)}개의 블록 생성됨. 저장: {output_file}")

    return results

if __name__ == "__main__":
    folder_path = "01_pre-processing/upstage_document_parse/temp/250313-17-20_20241220_[교재]_연말정산 세무_이석정_한국_회원_3.5시간65~68"
    process_folder(folder_path)
