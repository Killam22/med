# infrastructure/embeddings/encoder.py

import os
import logging

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"]       = "1"

from sentence_transformers import SentenceTransformer
from django.conf import settings

logger = logging.getLogger(__name__)

_model = None

def get_encoder() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Chargement modèle embedding: %s", settings.EMBEDDING_MODEL)
        _model = SentenceTransformer(
            settings.EMBEDDING_MODEL,
            local_files_only=True
        )
        logger.info(
            "Modèle embedding prêt — dimensions: %d",
            _model.get_sentence_embedding_dimension()
        )
    return _model


def encode(texts: list) -> list:
    model = get_encoder()
    # multilingual-e5-large nécessite le préfixe "query: " pour les recherches
    prefixed = [f"query: {t}" for t in texts]
    return model.encode(
        prefixed,
        normalize_embeddings=True,
        show_progress_bar=False
    ).tolist()