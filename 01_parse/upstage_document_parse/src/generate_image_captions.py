import os
import sys
import json
import base64
import re
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

def load_result(base_folder):
    """
    base_folder 내에서 _result.json으로 끝나는 파일을 찾아 로드합니다.
    """
    for fname in os.listdir(base_folder):
        if fname.endswith("_result.json"):
            result_path = os.path.join(base_folder, fname)
            with open(result_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
    return {}

def build_page_context_map(result):
    """
    result의 "pages" 리스트를 이용하여 {페이지번호: 내용} 매핑을 생성합니다.
    각 페이지의 내용은 "md"가 있으면 사용하고, 없으면 "text"를 사용합니다.
    만약 "pages" 키가 없으면, 단일 페이지(페이지 번호 1)로 처리합니다.
    """
    page_context = {}
    pages = result.get("pages")
    if pages:
        for page in pages:
            p_num = page.get("page")
            content = page.get("md") or page.get("text") or ""
            if p_num is not None:
                page_context[p_num] = content
    else:
        content = result.get("content", {}).get("markdown") or result.get("content", {}).get("text") or ""
        page_context[1] = content
    return page_context

def get_image_caption(image_path, api_key, prompt_context=""):
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        encoded_image = base64.b64encode(image_data).decode("utf-8")
        # PNG 형식의 data URL 생성 (입력 파일은 png라고 가정)
        data_url = f"data:image/png;base64,{encoded_image}"
    except Exception as e:
        return ""
    
    client = OpenAI(api_key=api_key)
    
    # 프롬프트 구성: 전달받은 prompt_context(해당 페이지의 내용)를 포함
    prompt = (
        """
        너는 이미지를 분석하고 이미지에 대한 설명을 해주는 어시스턴트야 오래걸려도 되니까 천천히 생각하면서 정확히 대답해. 인사말이나 이미지와 관련없는 말은 하지마 예를 들면(이미지를 분석한 내용은 다음과 같습니다) 이런거 하지마.
        대답은 무조건 한국어로 해야 하며, 이미지를 보고 알아낼 수 있는 모든 정보를 정밀하게 분석한 후 대답해.
        이미지가 표라면 읽어서 마크다운으로 만들어줘야해, 표에 병합된 부분이 있다면 병합을 풀때 내용이 누락되지 않도록 해당되는 모든 셀에 내용을 작성해야해 하나만 작성하면 안돼, 
        답변을 작성하기전에 반드시 한번 더 검토해보고나서 답변을 만들어
        내가말한 병합인 경우 병합해제를 하고 답변해야하며 텍스트가 누락되면 안되는걸 명심해.
        """
        + (f"\n아래는 해당 이미지가 있던 페이지의 내용이야:\n{prompt_context}" if prompt_context else "")
    )
    
    messages = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}}
    ]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": messages}],
            max_tokens=2000,
            temperature=0
        )
        caption = response.choices[0].message.content
        return caption
    except Exception as e:
        return ""

def process_image_file(filename, items_folder, page_context_map, api_key):
    """
    개별 이미지 파일을 처리하여 캡션을 생성하고, 결과를 파일에 저장합니다.
    만약 캡션 생성 결과가 None 또는 빈 문자열이면 한 번 더 요청하고,
    재시도 후에도 실패하면 "openAI 멀티모달 api오류"라는 텍스트를 사용합니다.
    """
    if not filename.lower().endswith(".png"):
        return None
    image_path = os.path.join(items_folder, filename)
    # 파일명에서 "_page_"와 그 뒤의 "_" 사이의 숫자를 추출 (예: "3_page_1_figure_1.png" → 페이지 번호 1)
    match = re.search(r'_page_(\d+)_', filename)
    page_num = int(match.group(1)) if match else None
    prompt_context = page_context_map.get(page_num, "") if page_num is not None else ""
    
    caption = get_image_caption(image_path, api_key, prompt_context)
    if not caption or caption.strip() == "":
        # 캡션이 None 또는 빈 문자열이면 재시도
        caption = get_image_caption(image_path, api_key, prompt_context)
        if not caption or caption.strip() == "":
            caption = "openAI 멀티모달 api오류"

    # ⚠️ 마크다운 블록 제거 (```markdown, ```)
    caption = re.sub(r"```markdown\s*", "<<markdown시작>>", caption)
    caption = caption.replace("```", "<<markdown종료>>")
    caption = escape_json_string(caption)

    # 결과 저장
    caption_filename = os.path.join(items_folder, f"{os.path.splitext(filename)[0]}_caption.txt")
    with open(caption_filename, "w", encoding="utf-8") as f:
        f.write(caption)
    
    return caption

def escape_json_string(s):
    return (
        s.replace("\\", "\\\\")   # 백슬래시 먼저
            .replace("\"", "\\\"")   # 큰따옴표
            .replace("/", "\\/")     # 슬래시 (선택적)
            .replace("\b", "\\b")    # 백스페이스
            .replace("\f", "\\f")    # 폼피드
            .replace("\n", "\\n")    # 줄바꿈
            .replace("\r", "\\r")    # 캐리지 리턴
            .replace("\t", "\\t")    # 탭
    )


def update_excel_with_captions(base_folder):
    """
    base_folder 내에 있는 엑셀 파일(.xlsx)을 열어,
    각 행의 alt 열에 기록된 이미지 파일명에 해당하는 캡션 파일을 Items 폴더에서 찾아,
    "이미지설명" 열에 캡션 텍스트를 업데이트합니다.
    이때 "이미지설명" 열은 NaN 대신 빈 문자열("")이 입력되도록 합니다.
    """
    base_name = os.path.basename(os.path.normpath(base_folder))
    excel_path = os.path.join(base_folder, f"{base_name}.xlsx")
    items_folder = os.path.join(base_folder, "Items")
    if not os.path.exists(excel_path):
        print("엑셀 파일이 존재하지 않습니다.")
        return
    
    df = pd.read_excel(excel_path)
    # "이미지설명" 열이 없으면 생성하고, 있다면 NaN을 빈 문자열로 채운 후 문자열로 변환
    if "이미지설명" not in df.columns:
        df["이미지설명"] = ""
    else:
        df["이미지설명"] = df["이미지설명"].fillna("").astype(str)
    
    # alt 열이 비어있지 않은 행에 대해 업데이트 시도
    for idx, row in df.iterrows():
        alt_val = str(row.get("alt", "")).strip()
        if alt_val:
            # alt_val가 콤마로 연결된 여러 파일명인 경우 split 처리
            img_names = [name.strip() for name in alt_val.split(",")]
            captions = []
            for img_name in img_names:
                # 캡션 파일명: 이미지 파일명에서 확장자를 제거하고 _caption.txt 추가
                base_img = os.path.splitext(img_name)[0]
                caption_file = os.path.join(items_folder, f"{base_img}_caption.txt")
                if os.path.exists(caption_file):
                    with open(caption_file, "r", encoding="utf-8") as f:
                        caption_text = f.read().strip()
                        if caption_text:
                            captions.append(caption_text)
            # 캡션들을 줄바꿈(\n)으로 연결하여 "이미지설명" 열에 업데이트
            if captions:
                df.at[idx, "이미지설명"] = "\n".join(captions)
    
    # 저장하기 전에 "이미지설명" 열의 NaN을 빈 문자열로 다시 한번 채웁니다.
    df["이미지설명"] = df["이미지설명"].fillna("").astype(str)
    
    df.to_excel(excel_path, index=False)
    print(f"║   -> 엑셀 파일에 이미지설명 업데이트 완료: {excel_path}")

def generate_captions(api_key, base_folder):
    """
    api_key: OPENAI API 키
    base_folder: _result.json와 "Items" 폴더가 포함된 폴더
    """
    load_dotenv()
    result = load_result(base_folder)
    if not result:
        print("결과 JSON 로드 실패.")
        return
    
    page_context_map = build_page_context_map(result)
    items_folder = os.path.join(base_folder, "Items")
    if not os.path.exists(items_folder):
        print(f"Items 폴더가 존재하지 않습니다: {items_folder}")
        return

    # Items 폴더 내의 png 파일들만 처리 (동시처리)
    filenames = [fname for fname in os.listdir(items_folder) if fname.lower().endswith(".png")]
    print("║ ✅ 이미지 캡션 작업")
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for filename in filenames:
            futures.append(executor.submit(process_image_file, filename, items_folder, page_context_map, api_key))
        for future in tqdm(as_completed(futures), total=len(futures), desc="║   -> 이미지 캡션 생성"):
            future.result()
            
    print(f"║   -> 이미지 캡션 생성 및 저장 완료. -> {base_folder}")
    # 캡션 생성 후 엑셀 파일 업데이트
    update_excel_with_captions(base_folder)

if __name__ == "__main__":
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
    
    # 테스트용 base_folder (사용자가 직접 지정)
    base_folder = r"C:\Users\yoyo2\fas\RAG_Pre_processing\data\250331-13-07_모니터1~3p"
    generate_captions(OPENAI_API_KEY, base_folder)
