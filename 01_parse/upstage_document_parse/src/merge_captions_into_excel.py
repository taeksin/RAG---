import os
import sys
import pandas as pd

def merge_captions_into_excel(base_folder):
    # base_folder 내의 .xlsx 파일 찾기 (하나만 존재한다고 가정)
    excel_files = [f for f in os.listdir(base_folder) if f.endswith(".xlsx")]
    if not excel_files:
        print("Excel 파일을 찾을 수 없습니다.")
        return
    if len(excel_files) > 1:
        print("여러 Excel 파일이 존재합니다. 첫번째 파일을 사용합니다.")
    excel_file = os.path.join(base_folder, excel_files[0])
    
    # Excel 파일 읽기
    df = pd.read_excel(excel_file)
    
    # items 폴더 경로 지정
    items_folder = os.path.join(base_folder, "items")
    if not os.path.exists(items_folder):
        print("items 폴더가 존재하지 않습니다.")
        return

    # items 폴더 내의 *_caption.txt 파일들 처리
    for file in os.listdir(items_folder):
        if file.endswith("_caption.txt"):
            caption_file_path = os.path.join(items_folder, file)
            with open(caption_file_path, "r", encoding="utf-8") as f:
                caption_text = f.read().strip()
            # 예: "2_page_1_table_1_caption.txt" -> "2_page_1_table_1.png"
            image_name = file.replace("_caption.txt", ".png")
            
            # alt 컬럼에서 image_name과 일치하는 행 찾기
            matching_rows = df['alt'] == image_name
            if matching_rows.any():
                df.loc[matching_rows, "이미지설명"] = caption_text
                print(f"{image_name} 에 대한 캡션을 병합했습니다.")
            else:
                print(f"{image_name} 에 해당하는 행을 Excel에서 찾지 못했습니다.")
    
    # 변경된 DataFrame을 Excel 파일에 저장 (덮어쓰기)
    df.to_excel(excel_file, index=False)
    print("Excel 파일 저장이 완료되었습니다.")

if __name__ == "__main__":
    base_folder = r"C:\Users\yoyo2\fas\RAG_Pre_processing\data\250331-12-56_모니터1~3p"
    merge_captions_into_excel(base_folder)
