# split_pdf.py
import os
import pymupdf  # PyMuPDF 라이브러리

def split_pdf(filepath, batch_size=50):
    """
    입력 PDF를 여러 개의 작은 PDF 파일로 분할하는 함수.
    분할된 파일명은 원본 파일명에 시작페이지와 끝페이지 번호를 추가합니다.
    예: 파일명_1~50.pdf, 파일명_51~100.pdf, ...
    """
    input_pdf = pymupdf.open(filepath)
    num_pages = len(input_pdf)
    print(f"총 페이지 수: {num_pages}")

    ret = []
    input_file_basename = os.path.splitext(filepath)[0]

    for start_page in range(0, num_pages, batch_size):
        end_page = min(start_page + batch_size, num_pages) - 1
        # 사람 눈에 보이는 번호는 1부터 시작하므로 start_page+1, end_page+1 사용
        output_file = f"{input_file_basename}_{start_page+1}~{end_page+1}.pdf"
        print(f"📂 분할된 PDF 생성: {output_file}")

        with pymupdf.open() as output_pdf:
            output_pdf.insert_pdf(input_pdf, from_page=start_page, to_page=end_page)
            output_pdf.save(output_file)

        ret.append(output_file)

    input_pdf.close()
    return ret
