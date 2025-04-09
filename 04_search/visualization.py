import pandas as pd

def create_visualization_2d(embeddings_array, texts, query_embedding=None, query_text=None):
    """
    2D 시각화를 위해 주어진 문서 임베딩 배열을 PCA로 2차원으로 축소하고,
    Plotly Express를 사용하여 산점도 형태의 시각화를 생성합니다.
    
    Args:
        embeddings_array: 문서 임베딩이 저장된 numpy 배열.
        texts (list[str]): 각 문서의 텍스트 리스트.
        query_embedding (numpy array, optional): 검색 쿼리의 임베딩 (2D 배열).
        query_text (str, optional): 검색한 쿼리 텍스트.
    
    Returns:
        fig: 생성된 2D Plotly figure 객체.
    """
    from sklearn.decomposition import PCA
    import plotly.express as px
    import plotly.graph_objects as go

    # PCA를 사용하여 2차원으로 축소
    pca = PCA(n_components=2)
    reduced = pca.fit_transform(embeddings_array)
    df = pd.DataFrame(reduced, columns=['X축', 'Y축'])
    df['text'] = [t[:15] for t in texts]

    # 산점도 생성
    fig = px.scatter(df, x='X축', y='Y축', text='text', title='검색 결과 임베딩 2D 시각화 (PCA)')
    fig.update_traces(textposition='top center', marker=dict(size=6))

    # 검색 쿼리 표시 (빨간색 점)
    if query_embedding is not None and query_text is not None:
        query_reduced = pca.transform(query_embedding)
        fig.add_trace(
            go.Scatter(
                x=[query_reduced[0, 0]],
                y=[query_reduced[0, 1]],
                mode='markers+text',
                marker=dict(size=8, color='red'),
                text=[query_text],
                name='Query'
            )
        )
    return fig

def create_visualization_3d(embeddings_array, texts, query_embedding=None, query_text=None):
    """
    3D 시각화를 위해 주어진 문서 임베딩 배열을 PCA로 3차원으로 축소하고,
    Plotly Express를 사용하여 3D 산점도 형태의 시각화를 생성합니다.
    
    Args:
        embeddings_array: 문서 임베딩이 저장된 numpy 배열.
        texts (list[str]): 각 문서의 텍스트 리스트.
        query_embedding (numpy array, optional): 검색 쿼리의 임베딩 (2D 배열).
        query_text (str, optional): 검색한 쿼리 텍스트.
    
    Returns:
        fig: 생성된 3D Plotly figure 객체.
    """
    from sklearn.decomposition import PCA
    import plotly.express as px
    import plotly.graph_objects as go

    # PCA를 사용하여 3차원으로 축소
    pca = PCA(n_components=3)
    reduced = pca.fit_transform(embeddings_array)
    df = pd.DataFrame(reduced, columns=['X축', 'Y축', 'Z축'])
    df['text'] = [t[:15] for t in texts]

    # 3D 산점도 생성
    fig = px.scatter_3d(df, x='X축', y='Y축', z='Z축', text='text', title='검색 결과 임베딩 3D 시각화 (PCA)')
    fig.update_traces(textposition='top center', marker=dict(size=5))

    # 검색 쿼리 표시 (빨간색 점)
    if query_embedding is not None and query_text is not None:
        query_reduced = pca.transform(query_embedding)
        fig.add_trace(
            go.Scatter3d(
                x=[query_reduced[0, 0]],
                y=[query_reduced[0, 1]],
                z=[query_reduced[0, 2]],
                mode='markers+text',
                marker=dict(size=8, color='red'),
                text=[query_text],
                name='Query'
            )
        )
    return fig
