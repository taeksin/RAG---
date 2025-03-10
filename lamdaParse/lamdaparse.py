import os
import json
import requests
import fitz  # PyMuPDF
from dotenv import load_dotenv
from datetime import datetime

# .env 파일에서 API 키 로드
load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

# LlamaParse API 엔드포인트 (예시 URL, 실제 API 문서에 따라 수정)
LAMDA_API_URL = "https://api.llamaparser.com/v1/parse"

def crop_pdf_region(pdf_path, page_number, coordinates, output_path):
    """
    PDF 파일에서 특정 영역을 크롭하여 이미지로 저장.
    
    :param pdf_path: 원본 PDF 파일 경로
    :param page_number: 크롭할 페이지 번호 (1부터 시작)
    :param coordinates: [[x1, y1], [x2, y2], ...] 형태 (픽셀 좌표)
    :param output_path: 저장할 이미지 파일 경로
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number - 1)  # 0-based index
    
    xs = [pt[0] for pt in coordinates]
    ys = [pt[1] for pt in coordinates]
    x1, y1 = min(xs), min(ys)
    x2, y2 = max(xs), max(ys)
    
    # 크롭 좌표 검증
    if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1:
        print(f"❌ 잘못된 크롭 좌표: ({x1}, {y1}) - ({x2}, {y2}) → 크롭 건너뜀")
        return
    
    rect = fitz.Rect(x1, y1, x2, y2)
    pix = page.get_pixmap(clip=rect)
    
    # 픽셀 크기 검증
    if pix.width == 0 or pix.height == 0:
        print(f"⚠️ 유효하지 않은 크롭 영역 (너비={pix.width}, 높이={pix.height}) → 저장 건너뜀")
        return
    
    pix.save(output_path)
    print(f"✅ 크롭 이미지 저장 완료: {output_path}")

def parse_pdf_with_llamaparser(pdf_path):
    """
    LlamaParse API를 사용하여 PDF 파일을 파싱.
    API 키는 .env에서 로드하며, 결과로 JSON 데이터를 반환합니다.
    
    :param pdf_path: 처리할 PDF 파일 경로
    :return: 파싱 결과 JSON 데이터 (dict)
    """
    with open(pdf_path, "rb") as f:
        files = {"document": f}
        headers = {"Authorization": f"Bearer {API_KEY}"}
        # API 요청 파라미터 (예시)
        data = {
            "output_formats": '["html", "text", "markdown"]',
            "ocr": "force",
            "model": "llamaparser"
        }
        print(f"📤 PDF 파일 {pdf_path} 을(를) LlamaParse API에 업로드 중...")
        response = requests.post(LAMDA_API_URL, headers=headers, files=files, data=data)
    
    if response.status_code == 200:
        print("📥 LlamaParse API 응답 수신 완료!")
        result = response.json()
        # JSON 결과 저장 (확인용)
        json_folder = "llamaparser/converted_documents"
        os.makedirs(json_folder, exist_ok=True)
        json_filename = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_llama_result.json"
        json_path = os.path.join(json_folder, json_filename)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"📄 JSON 결과가 저장되었습니다: {json_path}")
        return result
    else:
        print(f"❌ API 요청 실패: 상태 코드 {response.status_code}, 메시지: {response.text}")
        return None

def process_parsed_result(pdf_path, result):
    """
    파싱 결과 JSON 데이터를 바탕으로, 텍스트와 이미지(차트, 표 등) 요소를 추출하여
    Markdown 문서로 저장합니다. 이미지, 차트, 표는 해당 영역을 캡쳐하여 저장합니다.
    
    :param pdf_path: 원본 PDF 파일 경로
    :param result: LlamaParse API 반환 JSON 데이터
    :return: 생성된 Markdown 파일 경로
    """
    # 결과 JSON에서 elements는 리스트로 있다고 가정합니다.
    elements = result.get("elements", [])
    
    base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
    images_folder = os.path.join("llamaparser/output_images", base_filename)
    os.makedirs(images_folder, exist_ok=True)
    
    md_content = []
    
    for idx, element in enumerate(elements):
        # 각 element는 dict 형태이며, "category", "text", "metadata" 등의 키가 있다고 가정
        category = element.get("category", "").lower()
        text = element.get("text", "").strip()
        metadata = element.get("metadata", {})
        
        # 이미지, 차트, 표는 캡쳐해서 이미지 파일로 저장
        if category in ["image", "chart", "table"]:
            coordinates = metadata.get("coordinates")
            page_number = metadata.get("page_number", 1)
            if coordinates:
                image_filename = f"{base_filename}_element_{idx+1}.png"
                image_path = os.path.join(images_folder, image_filename)
                # coordinates는 [[x1, y1], [x2, y2], ...] 형태(픽셀 좌표)라고 가정
                crop_pdf_region(pdf_path, page_number, coordinates, image_path)
                # Markdown에는 상대 경로를 "../output_images/..." 형식으로 기록
                relative_image_path = f"../output_images/{base_filename}/{image_filename}"
                md_content.append(f"![{category.capitalize()}]({relative_image_path})\n")
        
        # 일반 텍스트 추가 (각 요소를 별도의 Markdown 섹션으로)
        if text:
            md_content.append(f"### {category.capitalize()} Element {idx+1}\n{text}\n")
    
    # 최종 Markdown 파일 생성
    output_folder = "llamaparser/converted_documents"
    os.makedirs(output_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    md_filename = f"{base_filename}_{timestamp}.md"
    output_md_path = os.path.join(output_folder, md_filename)
    
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(md_content))
    
    print(f"🎉 Markdown 파일이 저장되었습니다: {output_md_path}")
    return output_md_path

if __name__ == "__main__":
    pdf_file = "pdf/your_pdf_file.pdf"  # PDF 파일 경로를 실제 파일로 변경하세요.
    result = parse_pdf_with_llamaparser(pdf_file)
    if result:
        process_parsed_result(pdf_file, result)
