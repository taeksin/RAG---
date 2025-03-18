import os
import shutil

# overlap 크기보다 이전 블록의 크기가 작을 경우 
# 이전의 이전 블록까지 사용하는게 아니라
# 이전 블록 까지만 사용하도록 SPLIT함

def process_file(file_path):
    # 1. 파일 경로 및 복사본 파일 설정
    # 파일 경로에서 디렉토리와 파일명을 분리
    dir_name, base_name = os.path.split(file_path)
    # 복사본 파일명을 원본 파일명 앞에 '02_'를 붙여 생성
    new_file_name = "02_" + base_name
    new_file_path = os.path.join(dir_name, new_file_name)

    # 2. 원본 파일 복사
    # 원본 파일을 복사하여 새로운 파일 생성 (파일 속성 포함)
    shutil.copy2(file_path, new_file_path)

    # 3. 복사본 파일에서 텍스트 읽기
    with open(new_file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # 4. 기존 <<SPLIT>>가 남아있을 경우, <<BLOCKEND>>로 변경 (일관성 유지)
    content = content.replace("<<SPLIT>>", "<<BLOCKEND>>")

    # 5. <<BLOCKEND>>를 기준으로 블록 분리
    raw_blocks = content.split("<<BLOCKEND>>")
    
    # 6. 블록을 정리하여 빈 블록을 제거
    blocks = []
    for block in raw_blocks:
        block = block.strip()  # 앞뒤 공백 제거
        if block:  # 빈 블록은 제외
            blocks.append(block)

    # 7. 각 블록을 헤더(elementId: ...)와 내용으로 분리
    parsed_blocks = []
    for block in blocks:
        lines = block.splitlines()  # 줄 단위로 나누기
        if lines:
            header = lines[0]  # 첫 번째 줄은 elementId 헤더
            body = "\n".join(lines[1:]) if len(lines) > 1 else ""  # 나머지는 본문
            parsed_blocks.append((header, body))
        else:
            parsed_blocks.append(("", ""))  # 빈 블록이 있을 경우 예외 처리

    # 8. 블록별 오버랩 적용
    # - 두 번째 블록부터 이전 블록의 마지막 100자를 가져와 현재 블록의 본문 앞에 추가
    overlapped_blocks = []
    overlap_length = 100  # 오버랩 길이 설정
    for i, (header, body) in enumerate(parsed_blocks):
        if i > 0:
            prev_body = parsed_blocks[i-1][1]  # 이전 블록의 본문 가져오기
            # 이전 블록의 길이가 100자보다 짧으면 전체 내용을 오버랩
            overlap = prev_body[-overlap_length:] if len(prev_body) >= overlap_length else prev_body
            body = overlap + "\n" + body  # 오버랩된 내용을 현재 블록 앞에 추가
        overlapped_blocks.append((header, body))

    # 9. 오버랩이 적용된 블록들을 다시 <<SPLIT>> 구분자로 결합하여 최종 콘텐츠 생성
    modified_blocks = []
    for header, body in overlapped_blocks:
        block_text = header + "\n" + body if body else header  # 헤더 + 본문 결합
        modified_blocks.append(block_text)

    # 10. 최종 수정된 콘텐츠 생성 (각 블록을 <<SPLIT>>로 구분)
    modified_content = ("\n<<SPLIT>>\n").join(modified_blocks) + "\n<<SPLIT>>"

    # 11. 변경된 내용을 복사본 파일에 다시 저장
    with open(new_file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)

    # 12. 완료 메시지 출력
    print(f" -> 오버랩 적용 완료: {new_file_path}")

# 예제 실행 코드 (스크립트 직접 실행 시 동작)
if __name__ == "__main__":
    file_path = "01_pre-processing/upstage_document_parse/temp/250317-15-53_20241220_[보조교재]_연말정산 세무_이석정_한국_회원_3.5시간/250317-15-53_20241220_[보조교재]_연말정산 세무_이석정_한국_회원_3.5시간_merged.md"
    process_file(file_path)
