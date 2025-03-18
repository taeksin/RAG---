# generate_image_captions.py
import os
import sys
import json
import base64
import re
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
        "너는 이미지를 분석하고 이미지에 대한 설명을 해주는 어시스턴트야. 인사말이나 이미지와 관련없는 말은 하지마 예를 들면(이미지를 분석한 내용은 다음과 같습니다) 이런거 하지마. "
        "대답은 무조건 한국어로 해야 하며, 이미지를 보고 알아낼 수 있는 모든 정보를 정밀하게 분석한 후 대답해.\n"
        "이미지가 표라면 읽어서 마크다운으로 만들어줘야해, 표에 병합된 부분이 있다면 병합을 풀때 내용이 누락되지 않도록 해당되는 모든 셀에 내용을 작성해야해 하나만 작성하면 안돼, 답변을 작성하기전에 반드시 한번 더 검토해보고나서 답변을 만들어"
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
    """
    if not filename.lower().endswith(".png"):
        return
    image_path = os.path.join(items_folder, filename)
    # 파일명에서 "_page_"와 그 뒤의 "_" 사이의 숫자를 추출 (예: "3_page_1_figure_1.png" → 페이지 번호 1)
    match = re.search(r'_page_(\d+)_', filename)
    page_num = int(match.group(1)) if match else None
    prompt_context = page_context_map.get(page_num, "") if page_num is not None else ""
    caption = get_image_caption(image_path, api_key, prompt_context)
    caption_filename = os.path.join(items_folder, f"{os.path.splitext(filename)[0]}_caption.txt")
    with open(caption_filename, "w", encoding="utf-8") as f:
        f.write(caption)

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
    
    # ThreadPoolExecutor를 사용하여 병렬 처리 (적절한 워커 수 선택)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for filename in filenames:
            futures.append(executor.submit(process_image_file, filename, items_folder, page_context_map, api_key))
        for future in tqdm(as_completed(futures), total=len(futures), desc="이미지 캡션 생성"):
            # 각 future의 결과는 None이므로, 단순히 기다림
            future.result()
    print("이미지 캡션 생성 완료.")

if __name__ == "__main__":
    load_dotenv()
    UPSTAGE_API_KEY, OPENAI_API_KEY = map(os.getenv, ["UPSTAGE_API_KEY", "OPENAI_API_KEY"])
    if not (UPSTAGE_API_KEY and OPENAI_API_KEY):
        raise ValueError("환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
    
    # 테스트용 base_folder (사용자가 직접 지정)
    base_folder = "01_pre_processing/upstage_document_parse/temp/250317-15-53_20241220_[보조교재]_연말정산 세무_이석정_한국_회원_3.5시간"
    generate_captions(OPENAI_API_KEY, base_folder)
