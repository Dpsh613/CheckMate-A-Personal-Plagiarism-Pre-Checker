import gc
from fastembed import TextEmbedding

_model = None

def get_model():
    global _model
    if _model is None:
        _model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")
    return _model

def encode_texts(texts):
    if not texts:
        return []
    model = get_model()
    embeddings = list(model.embed(texts))
    result = [e.tolist() for e in embeddings]
    gc.collect()
    return result
