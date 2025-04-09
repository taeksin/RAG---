import json

def load_db_options(filepath="db_options.json"):
    """
    db_options.json 파일을 읽어 DB 옵션을 파이썬 딕셔너리로 반환합니다.
    
    Parameters:
        filepath (str): JSON 파일 경로 (기본값: "db_options.json").
    
    Returns:
        dict: JSON 파일에 정의된 DB 옵션.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def get_document(docstore, doc_id):
    """
    docstore에서 주어진 doc_id에 해당하는 문서를 반환합니다.
    만약 docstore가 InMemoryDocstore라면 내부 _dict를 사용하여 문서를 찾습니다.
    
    Parameters:
        docstore: 문서를 저장하는 객체 (딕셔너리 또는 InMemoryDocstore).
        doc_id: 반환할 문서의 식별자.
    
    Returns:
        문서 객체: doc_id에 해당하는 문서.
    """
    if hasattr(docstore, '_dict'):
        return docstore._dict[doc_id]
    else:
        return docstore[doc_id]
