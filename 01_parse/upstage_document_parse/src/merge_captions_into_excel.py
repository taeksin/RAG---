import os
import sys
import pandas as pd

def merge_captions_into_excel(base_folder):
    # base_folder 내의 .xlsx 파일 찾기 (하나만 존재한다고 가정)
    excel_files = [f for f in os.listdir(base_folder) if f.endswith(".xlsx")]
    if not excel_files:
        print("║ Excel 파일을 찾을 수 없습니다.")
        return
    if len(excel_files) > 1:
        print("║ 여러 Excel 파일이 존재합니다. 첫번째 파일을 사용합니다.")
    excel_file = os.path.join(base_folder, excel_files[0])
    
    # Excel 파일 읽기
    df = pd.read_excel(excel_file)
    
    # items 폴더 경로 지정
    items_folder = os.path.join(base_folder, "items")
    if not os.path.exists(items_folder):
        print("║ items 폴더가 존재하지 않습니다.")
        return

    # Excel의 각 행에서 alt 열 값을 확인하여 처리
    for index, row in df.iterrows():
        alt_value = row.get("alt")
        if pd.isna(alt_value) or not isinstance(alt_value, str):
            continue
        # alt 열의 값이 ".png"로 끝나는 경우에만 처리
        if alt_value.endswith(".png"):
            # .png를 제거하여 caption 파일명 생성
            base_name = alt_value[:-4]  # ".png" 제거
            caption_file = base_name + "_caption.txt"
            caption_path = os.path.join(items_folder, caption_file)
            
            # caption 파일이 존재하는 경우 내용을 읽어 "이미지설명" 열에 기록
            if os.path.exists(caption_path):
                with open(caption_path, "r", encoding="utf-8") as f:
                    caption_text = f.read().strip()
                df.at[index, "이미지설명"] = caption_text
            else:
                print(f"║ 캡션 파일 '{caption_file}' 을(를) 찾을 수 없습니다. (Row {index}, alt: '{alt_value}')")
    
    # 변경된 DataFrame을 Excel 파일에 저장 (덮어쓰기)
    df.to_excel(excel_file, index=False)
    print("║   -> Excel 파일 저장이 완료되었습니다.")

if __name__ == "__main__":
    base_folder = r"C:\Users\yoyo2\fas\RAG_Pre_processing\data\250331-12-58_모니터1~3p"
    merge_captions_into_excel(base_folder)
