import os
import shutil

# 상수 정의: 청크 크기와 오버랩 크기
CHUNK_SIZE = 500     # 각 블록의 최대 길이 (청크)
OVERLAP_SIZE = 100   # 이전 블록에서 가져올 오버랩 길이

def process_file(file_path):
    """
    지정한 MD 파일을 열어서:
      1. "elementId:"로 시작하는 줄과 "<<BLOCKEND>>" 줄을 삭제
      2. 남은 텍스트를 하나의 긴 문자열로 만들고,
      3. CHUNK_SIZE와 OVERLAP_SIZE에 따라 슬라이딩 윈도우 방식으로 청크(블록)로 분할
      4. 각 청크 앞에 새 elementId를 추가하고, 블록 끝에 "<<BLOCKEND>>"를 추가하여 저장
    """
    # 1. 파일 경로 분리 및 복사본 파일 경로 생성
    dir_name, base_name = os.path.split(file_path)
    new_file_name = "04_" + base_name  # 새 파일명: 원본 파일명 앞에 '04_' 추가
    new_file_path = os.path.join(dir_name, new_file_name)

    # 2. 원본 파일 복사 (메타정보 포함)
    shutil.copy2(file_path, new_file_path)

    # 3. 복사본 파일의 텍스트 읽어오기
    with open(new_file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # 4. 파일 내에서 "elementId:"로 시작하는 줄과 "<<BLOCKEND>>" 줄 삭제
    #    각 줄별로 분리 후, 조건에 맞지 않는 줄만 다시 결합
    lines = content.splitlines()
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        # "elementId:"로 시작하거나, 줄 내용이 "<<BLOCKEND>>"이면 건너뜀
        if stripped.startswith("elementId:") or stripped == "<<BLOCKEND>>":
            continue
        filtered_lines.append(line)
    # 남은 줄들을 하나의 긴 텍스트로 결합 (개행 포함)
    full_text = "\n".join(filtered_lines).strip()

    # 5. 슬라이딩 윈도우 방식으로 텍스트를 청크로 분할
    #    step은 CHUNK_SIZE - OVERLAP_SIZE
    step = CHUNK_SIZE - OVERLAP_SIZE
    chunks = []
    for i in range(0, len(full_text), step):
        chunk = full_text[i:i+CHUNK_SIZE]
        chunks.append(chunk)

    # 6. 각 청크에 대해 새 elementId를 부여하고, 블록 형식으로 구성
    #    최종 블록 형식:
    #      (청크 내용; 첫 OVERLAP_SIZE는 이전 청크의 overlap 부분임)
    #      <<SPLIT>>
    blocks = []
    for idx, chunk in enumerate(chunks):
        block_text = f"{chunk}\n<<SPLIT>>"
        blocks.append(block_text)

    # 7. 모든 블록을 개행으로 결합하여 최종 콘텐츠 생성
    modified_content = "\n".join(blocks)

    # 8. 최종 수정된 내용을 새 파일에 저장
    with open(new_file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)

    print(f"-> 작업 완료: {new_file_path}")

# 예제 실행 코드
if __name__ == "__main__":
    file_path = "01_pre_processing/upstage_document_parse/temp/250314-17-45_모니터1~3p/250314-17-45_모니터1~3p_merged.md"
    process_file(file_path)
