# infrastructure/vector_db/chroma_client.py

import chromadb
import logging
from django.conf import settings

logger  = logging.getLogger(__name__)
_client = None


def get_client() -> chromadb.PersistentClient:
    """Retourne le client Chroma (singleton)."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        logger.info("Chroma client initialisé: %s", settings.CHROMA_PATH)
    return _client


def get_collection(name: str = "medical_common"):
    """
    Retourne une collection Chroma par nom.
    Par défaut retourne medical_common (rétrocompatibilité).
    """
    return get_client().get_collection(name)


def get_collection_stats() -> dict:
    """Retourne les stats des collections pour le health check."""
    try:
        client = get_client()
        stats  = {"status": "ok", "collections": {}}

        for col_name in ["medical_common", "medical_rare"]:
            try:
                col = client.get_collection(col_name)
                stats["collections"][col_name] = col.count()
            except Exception:
                stats["collections"][col_name] = "not found"

        # Rétrocompatibilité avec l'ancienne collection
        try:
            old = client.get_collection("medical_knowledge")
            stats["collections"]["medical_knowledge (legacy)"] = old.count()
        except Exception:
            pass

        return stats

    except Exception as e:
        return {"status": "error", "error": str(e)}