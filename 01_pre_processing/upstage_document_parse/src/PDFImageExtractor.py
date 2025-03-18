import os
import re
import sys
import fitz  # PyMuPDF
from PIL import Image

sys.dont_write_bytecode = True

class PDFImageExtractor:
    def __init__(self, pdf_file, dpi=300):
        """
        :param pdf_file: PDF 파일 경로 (파일명에 페이지범위가 포함되어 있어야 함, 예: "문서_51~100.pdf")
        :param dpi: 페이지 렌더링 해상도 (기본 300)
        """
        self.pdf_file = pdf_file
        self.dpi = dpi
        self.doc = fitz.open(pdf_file)
        # 파일명에서 시작 페이지 번호를 추출 (정규식 사용)
        base = os.path.basename(pdf_file)
        m = re.search(r'_(\d+)~(\d+)\.pdf$', base)
        if m:
            # 시작 페이지 (예: "51"이면 start_page = 51)
            self.start_page = int(m.group(1))
        else:
            self.start_page = 1  # 분할 정보가 없으면 1페이지부터 시작

    def get_page_image(self, page_number):
        """
        PDF의 해당 페이지(0-based 인덱스)를 PIL.Image 객체로 반환
        """
        page = self.doc.load_page(page_number)
        zoom = self.dpi / 72  # 72dpi 기준 배율 계산
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img

    @staticmethod
    def get_pixel_coordinates(coordinates, page_size):
        """
        normalized 좌표(0~1 사이)를 받아 실제 픽셀 좌표 (x1, y1, x2, y2)로 변환
        :param coordinates: [{'x': ..., 'y': ...}, ...] (정규화된 값)
        :param page_size: (width, height) 픽셀 단위
        :return: (x1, y1, x2, y2)
        """
        width, height = page_size
        xs = [pt["x"] for pt in coordinates]
        ys = [pt["y"] for pt in coordinates]
        x1 = int(min(xs) * width)
        y1 = int(min(ys) * height)
        x2 = int(max(xs) * width)
        y2 = int(max(ys) * height)
        return (x1, y1, x2, y2)

    def crop_and_save_element(self, element, out_dir, page_count):
        """
        요소의 좌표를 사용해 PDF 페이지에서 해당 영역을 크롭한 후 이미지로 저장
        :param element: API 응답 요소 (category, page, coordinates, id 등)
        :param out_dir: 이미지 파일 저장 폴더
        :param page_count: 해당 페이지 내에서 몇 번째 요소인지 (1-based)
        :return: 이미지가 저장된 파일 경로
        """
        # API 응답의 'id' 필드 추출
        element_id = element.get("id", None)
        if element_id is None:
            element_id = "noid"

        # relative_page: 분할 파일 기준 (API에서는 보통 1부터 시작)
        relative_page = element.get("page", 1)
        # 글로벌 페이지 번호: 시작 페이지 + (relative_page - 1)
        global_page = self.start_page + relative_page - 1

        if "coordinates" not in element or len(element["coordinates"]) < 4:
            print(f"⚠️ 요소의 좌표 정보가 부족합니다. (글로벌 페이지 {global_page})")
            return None

        # 분할 파일에서는 relative_page를 기준으로 페이지 이미지를 가져옴 (0-based 인덱스)
        img = self.get_page_image(relative_page - 1)
        page_size = img.size
        crop_coords = self.get_pixel_coordinates(element["coordinates"], page_size)
        cropped_img = img.crop(crop_coords)

        category = element.get("category", "unknown").lower()

        # 파일명: {element_id}_page_{global_page}_{category}_{page_count}.png
        filename = f"{element_id}_page_{global_page}_{category}_{page_count}.png"
        output_path = os.path.join(out_dir, filename)
        
        cropped_img.save(output_path)
        return output_path

    def extract_elements(self, elements, out_dir):
        """
        요소 리스트에서 카테고리가 chart, table, figure인 항목만 골라 크롭 및 저장
        :param elements: API 응답의 elements 리스트
        :param out_dir: 크롭한 이미지 저장 폴더
        :return: 추출된 모든 이미지 경로 리스트
        """
        os.makedirs(out_dir, exist_ok=True)
        
        # 페이지별, 카테고리별 순번을 관리할 딕셔너리
        counts = {}  # key: (relative_page, category) / value: count
        extracted_image_paths = []

        for element in elements:
            category = element.get("category", "").lower()
            if category in ["chart", "table", "figure"]:
                # relative page (API 결과)
                page = element.get("page", 1)
                key = (page, category)
                counts[key] = counts.get(key, 0) + 1

                img_path = self.crop_and_save_element(element, out_dir, counts[key])
                if img_path:
                    extracted_image_paths.append(img_path)

        return extracted_image_paths
