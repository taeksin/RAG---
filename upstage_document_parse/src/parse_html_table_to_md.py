import re
import sys
sys.dont_write_bytecode = True


def parse_html_table_to_md(table_elem):
    """
    HTML 테이블 -> Markdown 표 (rowspan/colspan 간단 처리).
    """
    all_tr = table_elem.find_all("tr")
    if not all_tr:
        return ""

    # (1) 열 개수 자동계산
    max_cols = 0
    for tr in all_tr:
        cells = tr.find_all(["td","th"])
        col_sum = 0
        for cell in cells:
            cspan = cell.get("colspan")
            cspan_val = int(cspan) if cspan and cspan.isdigit() else 1
            col_sum += cspan_val
        if col_sum > max_cols:
            max_cols = col_sum
    if max_cols <= 0:
        return ""

    # (2) rowspan/colspan 처리
    max_possible_rows = len(all_tr)*2
    table_matrix = [[None]*max_cols for _ in range(max_possible_rows)]
    used = [[False]*max_cols for _ in range(max_possible_rows)]
    current_row = 0

    for tr in all_tr:
        tds = tr.find_all(["td","th"])
        if not tds:
            current_row += 1
            continue

        while current_row < max_possible_rows and all(used[current_row]):
            current_row += 1
        if current_row >= max_possible_rows:
            break

        col_idx = 0
        for cell in tds:
            rspan = cell.get("rowspan")
            cspan = cell.get("colspan")
            row_span = int(rspan) if (rspan and rspan.isdigit()) else 1
            col_span = int(cspan) if (cspan and cspan.isdigit()) else 1
            cell_text = cell.get_text(" ", strip=True)

            while col_idx < max_cols and used[current_row][col_idx]:
                col_idx += 1
            if col_idx >= max_cols:
                break

            for rr in range(row_span):
                rr_row = current_row + rr
                if rr_row >= max_possible_rows:
                    break
                for cc in range(col_span):
                    cc_col = col_idx + cc
                    if cc_col >= max_cols:
                        break
                    table_matrix[rr_row][cc_col] = cell_text
                    used[rr_row][cc_col] = True
            col_idx += col_span

        current_row += 1

    last_filled_row = 0
    for r in range(max_possible_rows):
        if any(table_matrix[r][c] is not None for c in range(max_cols)):
            last_filled_row = r

    md_lines = []
    for r in range(last_filled_row+1):
        row_cells = [table_matrix[r][c] if table_matrix[r][c] else "" for c in range(max_cols)]
        md_lines.append("| " + " | ".join(row_cells) + " |")

    return "\n".join(md_lines)