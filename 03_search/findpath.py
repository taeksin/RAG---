import os

# 확인할 폴더 경로
folderpath = "./vdb/faiss/small/4_upstage_layout기준/"

# 현재 작업 디렉토리 출력
current_dir = os.getcwd()
print(f"현재 작업 디렉토리: {current_dir}")

# 폴더 존재 여부 확인
if os.path.isdir(folderpath):
    print(f"폴더가 존재합니다: {os.path.abspath(folderpath)}")
else:
    print(f"폴더가 존재하지 않습니다: {os.path.abspath(folderpath)}")
