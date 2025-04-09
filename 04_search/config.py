import json

def load_db_options(filepath="db_options.json"):
    """db_options.json 파일을 읽어 DB 옵션을 반환합니다."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def get_document(docstore, doc_id):
    """
    docstore에서 doc_id에 해당하는 문서를 반환합니다.
    docstore가 InMemoryDocstore라면 내부 _dict를 사용합니다.
    """
    if hasattr(docstore, '_dict'):
        return docstore._dict[doc_id]
    else:
        return docstore[doc_id]
