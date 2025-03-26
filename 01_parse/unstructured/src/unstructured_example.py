import os
import json
import time
import fitz  # PyMuPDF
from unstructured.partition.pdf import partition_pdf
from datetime import datetime

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

def process_pdf_to_markdown(pdf_path, languages=["kor", "eng"]):
    """
    PDF를 Unstructured를 사용하여 분석하고, 각 요소를 Markdown으로 변환하며,
    표, 텍스트, 이미지 정보를 포함하여 요소 단위로 Markdown 블록을 생성합니다.
    또한, 분석 결과 JSON을 파일로 저장하고, Unstructured 소요시간을 Markdown 파일 마지막에 추가합니다.
    
    :param pdf_path: 처리할 PDF 파일 경로
    :param languages: OCR에 사용할 언어 리스트 (예: ['kor', 'eng'])
    :return: 생성된 Markdown 파일 경로
    """
    start_time = time.time()  # 처리 시작 시간 기록
    
    # languages 인자는 반드시 문자열 리스트여야 함
    elements = partition_pdf(pdf_path, languages=languages)
    
    # Unstructured  소요시간 계산
    elapsed_time = time.time() - start_time
    print(f"⏱️ Unstructured  소요시간: {elapsed_time:.2f}초")
    
    # JSON 출력: 각 요소를 dict 형태로 변환하여 저장 (분석 결과 확인용)
    json_output = [element.to_dict() for element in elements]
    json_filename = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_elements.json"
    json_folder = "01_parse/unstructured/converted_documents"
    os.makedirs(json_folder, exist_ok=True)
    json_path = os.path.join(json_folder, json_filename)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=4)
    print(f"📄 JSON 분석 결과가 저장되었습니다: {json_path}")
    
    # Markdown 생성: 각 요소별로 처리 (헤더 없이 내용만 추가)
    base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
    images_folder = os.path.join("01_parse/unstructured/output_images", base_filename)
    os.makedirs(images_folder, exist_ok=True)
    
    md_content = []
    
    for idx, element in enumerate(elements):
        metadata = element.metadata  # ElementMetadata 객체
        text = element.text.strip() if element.text else ""
        
        block_md = ""  # 각 요소에 대한 블록
        
        # 좌표 정보가 있는 경우 이미지 크롭 수행 및 이미지 마크다운 추가
        coordinates_info = metadata.coordinates
        if coordinates_info and hasattr(coordinates_info, "points"):
            coords = coordinates_info.points  # 좌표는 픽셀 단위라고 가정
            page_number = getattr(metadata, "page_number", 1)
            image_filename = f"{base_filename}_element_{idx+1}.png"
            image_path = os.path.join(images_folder, image_filename)
            crop_pdf_region(pdf_path, page_number, coords, image_path)
            # 상대 경로는 항상 슬래시("/") 사용
            relative_image_path = f"../output_images/{base_filename}/{image_filename}"
            block_md += f"![Extracted Image]({relative_image_path})\n\n"
        
        # 일반 텍스트 추가
        if text:
            block_md += f"{text}\n"
        
        md_content.append(block_md)
    

    
    # 최종 Markdown 파일 생성 (각 요소별 Markdown 블록 포함)
    output_folder = "01_parse/unstructured/converted_documents"
    os.makedirs(output_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_filename = f"{base_filename}_{timestamp}.md"
    output_path = os.path.join(output_folder, output_filename)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(md_content))
    
    print(f"🎉 변환 완료! Markdown 파일이 저장되었습니다: {output_path}")
    return output_path

if __name__ == "__main__":
    pdf_file = "pdf/[꿈꾸는라이언]-3.pdf"
    process_pdf_to_markdown(pdf_file)
