import os
import json
import time
from dotenv import load_dotenv
from llama_parse import LlamaParse
import fitz  # PyMuPDF

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
pdf_path = "pdf/[꿈꾸는라이언]-3.pdf"

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

# JSON 저장
json_output_path = "lamdaParse/output/sample_parsed.json"
os.makedirs(os.path.dirname(json_output_path), exist_ok=True)
with open(json_output_path, "w", encoding="utf-8") as f:
    json.dump(json_list, f, ensure_ascii=False, indent=2)
print(f"✅ PDF 변환 완료! JSON 파일 저장됨: {json_output_path}")

# PyMuPDF로 PDF 열기
doc = fitz.open(pdf_path)

# 이미지 저장 폴더
images_dir = "lamdaParse/output/images"
os.makedirs(images_dir, exist_ok=True)

# Markdown 텍스트 초기화
final_md_text = ""

# 페이지별 처리
for page_json in json_list:
    page_num = page_json.get("page", 1)
    pdf_page = doc.load_page(page_num - 1)

    page_md = page_json.get("md", "")

    # 이미지 처리 및 Markdown 내에 삽입
    if "images" in page_json:
        for idx, image in enumerate(page_json["images"], start=1):
            x = image.get("x", 0)
            y = image.get("y", 0)
            width = image.get("width", 0)
            height = image.get("height", 0)

            # 좌표 보정 및 크롭 영역 지정
            rect = fitz.Rect(max(x, 0), max(y, 0), max(x + width, 0), max(y + height, 0))
            pix = pdf_page.get_pixmap(clip=rect)

            image_filename = f"img_p{page_num}_{idx}.png"
            image_path = os.path.join(images_dir, image_filename)
            pix.save(image_path)

            rel_path = os.path.relpath(image_path, os.path.dirname(json_output_path))
            image_md = f"\n![Image p{page_num}-{idx}]({rel_path})\n"
            
            # 이미지를 해당 내용과 함께 위치하도록 Markdown에 추가
            page_md += image_md

    # Markdown 텍스트와 이미지 결합
    final_md_text += page_md + "\n\n---\n\n"

# Markdown 저장
md_output_path = "lamdaParse/output/sample_parsed.md"
with open(md_output_path, "w", encoding="utf-8") as f:
    f.write(final_md_text)

# 소요 시간 출력
elapsed_time = time.time() - start_time
print(f"✅ Markdown 파일 생성 완료! MD 파일 저장됨: {md_output_path}")
print(f"⏱️ 총 소요시간: {elapsed_time:.2f}초")
