import os
import pymupdf  # PyMuPDF 라이브러리

def split_pdf(filepath, batch_size=10):
    """
    입력 PDF를 여러 개의 작은 PDF 파일로 분할하는 함수
    """

    # PDF 파일 열기
    input_pdf = pymupdf.open(filepath)
    num_pages = len(input_pdf)
    print(f"총 페이지 수: {num_pages}")

    ret = []  # 분할된 PDF 파일 경로를 저장할 리스트

    # PDF 분할 작업 수행
    for start_page in range(0, num_pages, batch_size):
        end_page = min(start_page + batch_size, num_pages) - 1

        # 분할된 PDF 저장 경로 설정
        input_file_basename = os.path.splitext(filepath)[0]
        output_file = f"{input_file_basename}_{start_page:04d}_{end_page:04d}.pdf"
        print(f"📂 분할된 PDF 생성: {output_file}")

        # PDF 파일 생성 및 저장
        with pymupdf.open() as output_pdf:
            output_pdf.insert_pdf(input_pdf, from_page=start_page, to_page=end_page)
            output_pdf.save(output_file)

        ret.append(output_file)  # 생성된 파일 경로 저장

    # 입력 PDF 파일 닫기
    input_pdf.close()

    return ret

