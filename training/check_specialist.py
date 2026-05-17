import os, sys
sys.stdout.reconfigure(encoding="utf-8")
_BACK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACK not in sys.path:
    sys.path.insert(0, _BACK)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
import django; django.setup()

from diagnostic_ai.infrastructure.vector_db.chroma_client import get_client

client = get_client()
common = client.get_collection("medical_common")
rare   = client.get_collection("medical_rare")

SEARCH_TERMS = ["dental caries", "caries", "tooth disorder", "tooth decay", "dental abscess"]

for term in SEARCH_TERMS:
    for coll_name, coll in [("common", common), ("rare", rare)]:
        results = coll.get(where={"name_en": {"$eq": term}}, include=["metadatas"])
        if results["metadatas"]:
            for m in results["metadatas"]:
                print(f"[{coll_name}] {m.get('name_en','?')!s:30} specialist={m.get('specialist','NONE')!r}  urgency={m.get('urgency','?')!r}")
