
from sentence_transformers import SentenceTransformer

_model = None

MODEL_NAME = "intfloat/multilingual-e5-small"


def get_model():
    global _model

    if _model is None:
        _model = SentenceTransformer(
            MODEL_NAME,
            device="cpu"
        )

    return _model


def generate_embeddings(texts):
    if not texts:
        return []

    model = get_model()

    prepared_texts = [
        f"passage: {text}"
        for text in texts
    ]

    vectors = model.encode(
        prepared_texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False
    )

    return vectors.tolist()


def generate_query_embedding(query):
    model = get_model()

    vector = model.encode(
        [f"query: {query}"],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False
    )

    return vector[0].tolist()
