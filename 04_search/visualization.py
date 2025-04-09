import pandas as pd

def create_visualization_2d(embeddings_array, texts, query_embedding=None, query_text=None):
    from sklearn.decomposition import PCA
    import plotly.express as px
    import plotly.graph_objects as go

    pca = PCA(n_components=2)
    reduced = pca.fit_transform(embeddings_array)
    df = pd.DataFrame(reduced, columns=['X축', 'Y축'])
    df['text'] = [t[:15] for t in texts]

    fig = px.scatter(df, x='X축', y='Y축', text='text', title='검색 결과 임베딩 2D 시각화 (PCA)')
    fig.update_traces(textposition='top center', marker=dict(size=6))

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
    from sklearn.decomposition import PCA
    import plotly.express as px
    import plotly.graph_objects as go

    pca = PCA(n_components=3)
    reduced = pca.fit_transform(embeddings_array)
    df = pd.DataFrame(reduced, columns=['X축', 'Y축', 'Z축'])
    df['text'] = [t[:15] for t in texts]

    fig = px.scatter_3d(df, x='X축', y='Y축', z='Z축', text='text', title='검색 결과 임베딩 3D 시각화 (PCA)')
    fig.update_traces(textposition='top center', marker=dict(size=5))

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
