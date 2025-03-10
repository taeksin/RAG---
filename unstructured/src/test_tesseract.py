from pdf2image import convert_from_path

# PDF를 이미지로 변환 (환경 변수에서 Poppler 자동 검색)
images = convert_from_path("pdf/모니터1p.pdf")

# 변환된 이미지 개수 확인
print(f"총 {len(images)}개의 페이지가 변환되었습니다.")
