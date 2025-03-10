from unstructured.partition.pdf import partition_pdf

pdf_filepath = 'pdf/모니터8p.pdf'

# OCR을 사용하여 한국어(kor)와 영어(eng) 읽기 설정
elements = partition_pdf(pdf_filepath, ocr_languages=["kor", "eng"], mode='elements')

# 결과 출력
print(f"총 {len(elements)}개의 페이지가 분석되었습니다.\n")
for i, element in enumerate(elements):  
    print(f"📄 페이지 {element.metadata.page_number} 내용:")
    print(element.text)
    print("=" * 80)
