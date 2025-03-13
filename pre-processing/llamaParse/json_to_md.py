# json_to_md.py
import os
import sys
import json
import fitz  # PyMuPDF
from datetime import datetime

def json_to_md(json_path, pdf_path, output_dir):
    # 입력 파일 존재 여부 확인
    if not os.path.exists(json_path):
        print(f"❌ JSON 파일을 찾을 수 없습니다: {json_path}")
        sys.exit(1)
    if not os.path.exists(pdf_path):
        print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
        sys.exit(1)
    
    # JSON 데이터 로드
    with open(json_path, "r", encoding="utf-8") as f:
        json_list = json.load(f)
    
    # 출력 폴더 생성
    os.makedirs(output_dir, exist_ok=True)
    # 이미지 저장용 폴더 생성 (output_dir/images)
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    # PDF 열기 (이미지 추출용)
    doc = fitz.open(pdf_path)
    
    final_md_text = ""
    
    # 각 페이지별 처리
    for page_json in json_list:
        page_num = page_json.get("page", 1)
        try:
            pdf_page = doc.load_page(page_num - 1)
        except Exception as e:
            print(f"페이지 {page_num} 로드 오류: {e}")
            continue
        
        page_md = page_json.get("md", "")
        
        # 이미지 정보가 있을 경우 처리
        if "images" in page_json:
            for idx, image in enumerate(page_json["images"], start=1):
                x = image.get("x", 0)
                y = image.get("y", 0)
                width = image.get("width", 0)
                height = image.get("height", 0)
                
                # 폭, 높이가 유효한지 확인
                if width <= 0 or height <= 0:
                    print(f"페이지 {page_num}의 이미지 {idx} 건너뛰기: width={width}, height={height}")
                    continue
                
                # 클립 영역 계산
                rect = fitz.Rect(max(x, 0), max(y, 0), max(x + width, 0), max(y + height, 0))
                if rect.width <= 0 or rect.height <= 0:
                    print(f"페이지 {page_num}의 이미지 {idx} 건너뛰기: 유효하지 않은 영역 {rect}")
                    continue
                
                try:
                    pix = pdf_page.get_pixmap(clip=rect)
                except Exception as e:
                    print(f"페이지 {page_num}의 이미지 {idx} 픽스맵 생성 오류: {e}")
                    continue
                
                image_filename = f"img_p{page_num}_{idx}.png"
                image_path = os.path.join(images_dir, image_filename)
                try:
                    pix.save(image_path)
                except Exception as e:
                    print(f"페이지 {page_num}의 이미지 {idx} 저장 오류: {e}")
                    continue
                
                # 출력 폴더 기준 상대 경로
                rel_path = os.path.relpath(image_path, output_dir)
                image_md = f"\n![Image p{page_num}-{idx}]({rel_path})\n"
                page_md += image_md
        
        final_md_text += page_md + "\n\n---\n\n"
    
    doc.close()
    
    # 저장 파일명: {YYMMDD_HHMM}_{원본PDF파일명}.md
    time_prefix = datetime.now().strftime("%y%m%d_%H%M")
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    md_output_path = os.path.join(output_dir, f"{time_prefix}_{base_name}.md")
    
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(final_md_text)
    
    print(f"✅ Markdown 파일 생성 완료! MD 파일 저장됨: {md_output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python json_to_md.py <json_file> <pdf_file> [output_dir]")
        sys.exit(1)
    
    json_file = sys.argv[1]
    pdf_file = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "output"
    
    json_to_md(json_file, pdf_file, output_dir)
