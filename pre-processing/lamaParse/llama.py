import os
import json
import time
from dotenv import load_dotenv
from llama_parse import LlamaParse
import fitz  # PyMuPDF
from json_to_md import json_to_md  # json_to_md.py에 정의된 함수를 임포트
from datetime import datetime

# 시작 시간 기록
start_time = time.time()

# 환경 변수 로드
load_dotenv()
llama_api_key = os.getenv("LLAMA_CLOUD_API_KEY")
if not llama_api_key:
    raise ValueError("❌ LLAMA_CLOUD_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요!")

# 파서 설정
parser = LlamaParse(
    api_key=llama_api_key,
    auto_mode=True,
    auto_mode_trigger_on_table_in_page=True,
    auto_mode_trigger_on_image_in_page=True
)

# PDF 경로
pdf_path = "pdf/모니터6~7p.pdf"

# PDF 존재 여부 확인
if not os.path.exists(pdf_path):
    raise FileNotFoundError(f"❌ 지정된 PDF 파일을 찾을 수 없습니다: {pdf_path}")

# PDF 파싱
json_objs = parser.get_json_result(pdf_path)
if not json_objs:
    raise ValueError("❌ PDF에서 데이터를 추출하지 못했습니다. LlamaParse 결과를 확인하세요.")

json_list = json_objs[0].get("pages", [])
if not json_list:
    raise ValueError("❌ 추출된 PDF 페이지 데이터가 없습니다.")

# 저장 파일명: {YYMMDD_HHMM}_{원본PDF파일명}_parsed.json
time_prefix = datetime.now().strftime("%y%m%d_%H%M")
base_name = os.path.splitext(os.path.basename(pdf_path))[0]
json_output_path = os.path.join("pre-processing/llamaParse/output", f"{time_prefix}_{base_name}_parsed.json")
os.makedirs(os.path.dirname(json_output_path), exist_ok=True)
with open(json_output_path, "w", encoding="utf-8") as f:
    json.dump(json_list, f, ensure_ascii=False, indent=2)
print(f"✅ PDF 변환 완료! JSON 파일 저장됨: {json_output_path}")

# json_to_md.py를 호출하여 JSON을 MD로 변환 (출력 폴더는 "llamaParse/output"로 지정)
output_dir = "pre-processing/llamaParse/output"
json_to_md(json_output_path, pdf_path, output_dir)

elapsed_time = time.time() - start_time
print(f"✅ Markdown 파일 생성 완료! (총 소요시간: {elapsed_time:.2f}초)")
