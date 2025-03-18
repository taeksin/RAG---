import os
import shutil

def get_overlap_text(parsed_blocks, current_index, overlap_length):
    """
    현재 블록(current_index) 바로 이전부터 거슬러 올라가며,
    그들의 본문(body)을 순서대로 누적하여, 누적된 텍스트의 길이가 overlap_length 이상이 될 때까지 모읍니다.
    이후, 누적된 텍스트의 마지막 overlap_length 만큼의 문자를 반환합니다.
    만약 누적된 텍스트의 길이가 overlap_length보다 작으면, 누적된 텍스트 전체를 반환합니다.
    """
    accumulated = ""
    idx = current_index - 1
    # 이전 블록부터 거슬러 올라가며 텍스트 누적
    while idx >= 0 and len(accumulated) < overlap_length:
        block_body = parsed_blocks[idx][1]  # idx번째 블록의 본문
        # 앞쪽에 추가해서 올바른 순서를 유지: 이전 블록의 내용이 먼저 나오도록 함
        if accumulated:
            accumulated = block_body + "\n" + accumulated
        else:
            accumulated = block_body
        idx -= 1
    # 누적된 텍스트의 길이가 overlap_length 이상이면 마지막 overlap_length만큼 반환
    if len(accumulated) >= overlap_length:
        return accumulated[-overlap_length:]
    else:
        return accumulated

def process_file(file_path):
    """
    지정한 MD 파일을 열어:
      - "elementId:"로 시작하는 줄과 "<<BLOCKEND>>" 줄을 기준으로 이미 블록화되어 있다고 가정하고,
      - 각 블록에서, 두 번째 이후 블록에 대해 OVERLAP_SIZE만큼의 텍스트를 이전 블록들에서 누적하여 확보한 후,
        현재 블록의 본문 앞에 추가합니다.
      - 최종 블록은 다음 형식으로 구성됩니다.
      
          elementId: ??
          (누적된 오버랩 텍스트)
          (현재 블록의 본문)
          <<BLOCKEND>>
    """
    # 1. 파일 경로 분리 및 새 파일 경로 생성
    dir_name, base_name = os.path.split(file_path)
    new_file_name = "03_" + base_name  # 새 파일명은 원본 파일명 앞에 '03_'를 붙임
    new_file_path = os.path.join(dir_name, new_file_name)

    # 2. 원본 파일을 복사 (메타정보 포함)
    shutil.copy2(file_path, new_file_path)

    # 3. 복사본 파일에서 텍스트 전체 읽어오기
    with open(new_file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # 4. 혹시 남아 있을 수 있는 <<SPLIT>>를 <<BLOCKEND>>로 통일 (블록 분리 기준으로 사용)
    content = content.replace("<<SPLIT>>", "<<BLOCKEND>>")

    # 5. <<BLOCKEND>>를 기준으로 블록 분리 후, 빈 블록 제거
    raw_blocks = content.split("<<BLOCKEND>>")
    blocks = [b.strip() for b in raw_blocks if b.strip()]

    # 6. 각 블록을 헤더와 본문으로 분리
    #    - 첫 번째 줄은 header (예: "elementId: 20")
    #    - 나머지 줄은 본문(body)으로 처리
    parsed_blocks = []
    for block in blocks:
        lines = block.splitlines()
        if lines:
            header = lines[0]
            body = "\n".join(lines[1:]) if len(lines) > 1 else ""
            parsed_blocks.append((header, body))

    # 7. OVERLAP_SIZE 설정 및 각 블록에 대해 오버랩 적용
    overlap_length = 100
    result_blocks = []
    for i, (header, body) in enumerate(parsed_blocks):
        if i == 0:
            # 첫 번째 블록은 그대로 사용
            out_body = body
        else:
            # 두 번째 이후 블록:
            # OVERLAP_SIZE만큼의 텍스트를 이전 블록들에서 누적하여 확보한 후, 현재 블록의 본문 앞에 추가
            overlap_text = get_overlap_text(parsed_blocks, i, overlap_length)
            out_body = overlap_text + "\n" + body
        result_blocks.append((header, out_body))

    # 8. 각 블록을 "헤더\n본문" 형식으로 결합하고, 블록 사이에 "<<SPLIT>>" 구분자 삽입
    final_blocks = []
    for header, out_body in result_blocks:
        block_text = header + "\n" + out_body if out_body else header
        final_blocks.append(block_text)
    modified_content = "\n<<SPLIT>>\n".join(final_blocks) + "\n<<SPLIT>>\n"

    # 9. 최종 수정된 내용을 새 파일에 저장
    with open(new_file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)
    print(f"-> 오버랩 적용 완료: {new_file_path}")

# 예제 실행 코드
if __name__ == "__main__":
    file_path = "01_pre-processing/upstage_document_parse/temp/250317-15-53_20241220_[보조교재]_연말정산 세무_이석정_한국_회원_3.5시간/250317-15-53_20241220_[보조교재]_연말정산 세무_이석정_한국_회원_3.5시간_merged.md"
    process_file(file_path)
