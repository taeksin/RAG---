import os
import shutil

def process_file_01(file_path):
    # 파일 경로에서 디렉토리와 파일명을 분리
    dir_name, base_name = os.path.split(file_path)
    # 복사본 파일명: 원본 파일명 앞에 '01_'를 붙임
    new_file_name = "01_" + base_name
    new_file_path = os.path.join(dir_name, new_file_name)

    # 원본 파일을 복사하여 복사본 파일 생성
    shutil.copy2(file_path, new_file_path)

    # 복사본 파일에서 텍스트를 읽어들임
    with open(new_file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # <<BLOCKEND>>를 <<SPLIT>>로 변경
    modified_content = content.replace("<<BLOCKEND>>", "<<SPLIT>>")

    # 변경된 내용을 복사본 파일에 다시 씀
    with open(new_file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)
    
    return new_file_path

# 예제 실행 코드
if __name__ == "__main__":
    file_path = "01_pre_processing/upstage_document_parse/temp/250314-17-45_모니터1~3p/250314-17-45_모니터1~3p_merged.md"
    process_file_01(file_path)
