import os
import pandas as pd
from tqdm import tqdm
from openpyxl import load_workbook
from openpyxl.styles import Alignment

def extract_neighbors_by_elementid(df):
    """
    content (chunk_with_neighbors) 생성 함수  
    → [[[[[[이전청크], [[[[[[현재청크], [[[[[[다음청크] 각각에 라벨을 붙여 결합
    """
    df["elementid"] = df["elementid"].astype(int)
    df_sorted = df.sort_values(by="elementid").reset_index(drop=True)
    elementid_to_content = dict(zip(df_sorted["elementid"], df_sorted["내용"]))
    content_list = []
    for eid in df_sorted["elementid"]:
        prev = elementid_to_content.get(eid - 1, "")
        curr = elementid_to_content.get(eid, "")
        next_ = elementid_to_content.get(eid + 1, "")
        parts = [
            "[[[[[[이전청크]", prev,
            "[[[[[[현재청크]", curr,
            "[[[[[[다음청크]", next_
        ]
        combined = "\n\n".join(parts)
        content_list.append(combined)
    return content_list

def extract_page_plus_chunk(df):
    """
    content (page_plus_chunk) 생성 함수  
    → [[[[[[현재페이지]전체 내용]과 [[[[[[현재청크]에 대해 라벨을 붙여 결합
    """
    df["페이지숫자"] = df["페이지숫자"].astype(str)
    page_to_all_text = df.groupby("페이지숫자")["내용"].apply(lambda x: "\n\n".join(x)).to_dict()
    content_list = []
    for _, row in df.iterrows():
        page = row["페이지숫자"]
        chunk = row["내용"]
        full_page = page_to_all_text.get(page, "")
        parts = [
            "[[[[[[현재페이지 전체내용]", full_page,
            "[[[[[[현재청크]", chunk
        ]
        combined = "\n\n".join(parts)
        content_list.append(combined)
    return content_list

def extract_page_only(df):
    """
    content (page_only) 생성 함수  
    → [[[[[[현재페이지 전체 내용]을 라벨과 함께 표시
    """
    df["페이지숫자"] = df["페이지숫자"].astype(str)
    page_to_all_text = df.groupby("페이지숫자")["내용"].apply(lambda x: "\n\n".join(x)).to_dict()
    content_list = []
    for _, row in df.iterrows():
        page = row["페이지숫자"]
        full_page = page_to_all_text.get(page, "")
        combined = "[[[[[[현재페이지 전체내용]\n\n" + full_page
        content_list.append(combined)
    return content_list

def get_neighbor_metadata(df):
    """
    metadata -1 생성 함수  
    → [[[[[[이전청크], [[[[[[현재청크], [[[[[[다음청크]를 라벨과 함께 결합
    """
    df["elementid"] = df["elementid"].astype(int)
    df_sorted = df.sort_values(by="elementid").reset_index(drop=True)
    elementid_to_content = dict(zip(df_sorted["elementid"], df_sorted["내용"]))
    metadata = []
    for eid in df_sorted["elementid"]:
        prev = elementid_to_content.get(eid - 1, "")
        curr = elementid_to_content.get(eid, "")
        next_ = elementid_to_content.get(eid + 1, "")
        parts = [
            "[[[[[[이전청크]", prev,
            "[[[[[[현재청크]", curr,
            "[[[[[[다음청크]", next_
        ]
        combined = "\n\n".join(parts)
        metadata.append(combined)
    return metadata

def get_3page_metadata(df):
    """
    metadata -2 생성 함수  
    → [[[[[[이전페이지], [[[[[[현재페이지], [[[[[[다음페이지] 전체 내용을 라벨과 함께 결합  
       (각각 현재 청크가 속한 페이지 기준으로 page-1, page, page+1)
    """
    df["페이지숫자"] = df["페이지숫자"].astype(int)
    page_to_text = df.groupby("페이지숫자")["내용"].apply(lambda x: "\n\n".join(x)).to_dict()
    metadata = []
    for _, row in df.iterrows():
        page = int(row["페이지숫자"])
        prev_page = page_to_text.get(page - 1, "")
        current_page = page_to_text.get(page, "")
        next_page = page_to_text.get(page + 1, "")
        parts = [
            "[[[[[[이전페이지]", prev_page,
            "[[[[[[현재페이지]", current_page,
            "[[[[[[다음페이지]", next_page
        ]
        combined = "\n\n".join(parts)
        metadata.append(combined)
    return metadata

def get_cross_page_metadata(df):
    """
    metadata -3 생성 함수  
    → [[[[[[현재페이지 전체 내용], [[[[[[이전페이지의 마지막 청크], [[[[[[다음페이지의 첫번째 청크]를 라벨과 함께 결합
    """
    df["elementid"] = df["elementid"].astype(int)
    df["페이지숫자"] = df["페이지숫자"].astype(int)
    # 각 페이지별로 정렬된 데이터와 전체 페이지 내용, 첫번째/마지막 청크 저장
    page_groups = df.groupby("페이지숫자")
    page_dict = {}
    for page, group in page_groups:
        group_sorted = group.sort_values("elementid")
        full_page = "\n\n".join(group_sorted["내용"].tolist())
        first_chunk = group_sorted.iloc[0]["내용"]
        last_chunk = group_sorted.iloc[-1]["내용"]
        page_dict[page] = {"full": full_page, "first": first_chunk, "last": last_chunk}
    
    metadata = []
    for _, row in df.iterrows():
        page = int(row["페이지숫자"])
        current_full = page_dict.get(page, {}).get("full", "")
        prev_last = page_dict.get(page - 1, {}).get("last", "")
        next_first = page_dict.get(page + 1, {}).get("first", "")
        parts = [
            "[[[[[[현재페이지 전체내용]", current_full,
            "[[[[[[이전페이지 마지막 청크]", prev_last,
            "[[[[[[다음페이지 첫번째 청크]", next_first
        ]
        combined = "\n\n".join(parts)
        metadata.append(combined)
    return metadata

def save_excel(content_list, metadata_list, output_path):
    # DataFrame 생성 후 엑셀 파일 저장
    out_df = pd.DataFrame({
        "content": content_list,
        "metadata": metadata_list
    })
    out_df.to_excel(output_path, index=False)
    
    # openpyxl을 사용하여 엑셀 서식 적용
    wb = load_workbook(output_path)
    ws = wb.active
    
    # 열 너비를 80으로 설정 (A열: content, B열: metadata)
    ws.column_dimensions['A'].width = 80
    ws.column_dimensions['B'].width = 80
    
    # 각 셀에 대해 자동 줄바꿈 및 위쪽 정렬 적용
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            
    wb.save(output_path)

def construct_embedding_contents(base_folder):
    base_name = os.path.basename(os.path.normpath(base_folder))
    excel_path = os.path.join(base_folder, f"{base_name}.xlsx")
    if not os.path.exists(excel_path):
        print(f"❌ 엑셀 파일이 존재하지 않습니다: {excel_path}")
        return

    df = pd.read_excel(excel_path)
    os.makedirs(os.path.join(base_folder, "before"), exist_ok=True)

    # content 생성: key는 content의 종류를 나타냄.
    content_map = {
        "chunk_only": df["내용"].tolist(),  # 원본 청크 내용 그대로 사용
        "chunk_with_neighbors": extract_neighbors_by_elementid(df),
        "page_plus_chunk": extract_page_plus_chunk(df),
        "page_only": extract_page_only(df)
    }
    
    # content type에 따른 번호 매핑
    content_type_mapping = {
        "chunk_only": "1",
        "chunk_with_neighbors": "2",
        "page_plus_chunk": "3",
        "page_only": "4"
    }
    
    # 메타데이터 함수 매핑
    metadata_funcs = {
        "1": get_neighbor_metadata,
        "2": get_3page_metadata,
        "3": get_cross_page_metadata
    }
    
    # 각 content type마다 메타데이터 suffix 지정:
    # chunk_only, chunk_with_neighbors, page_plus_chunk는 -1, -2, -3 생성
    # page_only는 -1, -2만 생성
    for content_name, content_list in content_map.items():
        if content_name == "page_only":
            valid_meta_ids = ["2", "3"]
        else:
            valid_meta_ids = ["1", "2", "3"]
        
        for meta_id in valid_meta_ids:
            metadata_list = metadata_funcs[meta_id](df)
            filename = f"{content_type_mapping[content_name]}-{meta_id}_{content_name}.xlsx"
            save_path = os.path.join(base_folder, "before", filename)
            save_excel(content_list, metadata_list, save_path)


    print("📁 총 11개의 content|metadata 엑셀 파일이 생성되었습니다.")

if __name__ == "__main__":
    base_folder = "data/250331-11-33_모니터1~3p"
    construct_embedding_contents(base_folder)
