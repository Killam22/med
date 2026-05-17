"""
Correction précise des spécialistes erronés dans ChromaDB.
Évite les faux positifs (ex : Charcot-Marie-Tooth = neuropathie, pas dentaire).
"""
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

# Corrections explicites : (name_en exact ou substring) → specialist attendu
# On évite les faux positifs avec des keywords trop larges (ex: "tooth" seul)
DENTAL_EXACT = {
    "dental caries", "caries", "tooth decay", "toothache",
    "tooth abscess", "dental abscess", "gum disease",
    "gingivitis", "periodontitis", "pulpitis",
    "dental health", "dental health topics",
    "teething", "teething syndrome",
}
# Mots SPÉCIFIQUES au domaine dentaire (pas "tooth" seul car Charcot-Marie-Tooth)
DENTAL_SUBSTRINGS = [
    "dental cari", "dental abscess", "tooth decay", "toothache",
    "gum disease", "gingivit", "periodont", "pulpit",
    "orthodont",
]
# Maladies génétiques rares dont le nom contient "tooth" mais = neurologie
NEUROLOGICAL_KEEP = [
    "charcot-marie-tooth", "charcot marie tooth",
]
# ORL spécifique
ORL_EXACT = {
    "otitis media", "ear infection", "otitis",
    "sinusitis", "rhinitis", "allergic rhinitis",
    "pharyngitis", "tonsillitis", "laryngitis",
}
ORL_SUBSTRINGS = ["otitis", "rhinit", "sinusit", "pharyngit", "tonsill", "laryngit"]

fixed = 0
reverted = 0

for coll_name, coll in [("common", common), ("rare", rare)]:
    all_items = coll.get(include=["metadatas"])
    ids   = all_items["ids"]
    metas = all_items["metadatas"]

    for doc_id, meta in zip(ids, metas):
        name = (meta.get("name_en") or "").lower()
        current_spec = meta.get("specialist", "")

        # ── Annuler les Charcot-Marie-Tooth mal classés ──────────
        if any(kw in name for kw in NEUROLOGICAL_KEEP):
            if current_spec != "neurologue":
                new_meta = dict(meta)
                new_meta["specialist"] = "neurologue"
                coll.update(ids=[doc_id], metadatas=[new_meta])
                print(f"  REVERT [{coll_name}] {meta.get('name_en','?')!s:45} {current_spec!r} → 'neurologue'")
                reverted += 1
            continue

        # ── Corriger dental → dentiste ───────────────────────────
        is_dental = (name in DENTAL_EXACT or
                     any(kw in name for kw in DENTAL_SUBSTRINGS))
        if is_dental and current_spec != "dentiste":
            new_meta = dict(meta)
            new_meta["specialist"] = "dentiste"
            coll.update(ids=[doc_id], metadatas=[new_meta])
            print(f"  FIX   [{coll_name}] {meta.get('name_en','?')!s:45} {current_spec!r} → 'dentiste'")
            fixed += 1
            continue

        # ── Corriger ORL ─────────────────────────────────────────
        is_orl = (name in ORL_EXACT or
                  any(kw in name for kw in ORL_SUBSTRINGS))
        if is_orl and current_spec not in ("ORL", "dentiste"):
            new_meta = dict(meta)
            new_meta["specialist"] = "ORL"
            coll.update(ids=[doc_id], metadatas=[new_meta])
            print(f"  FIX   [{coll_name}] {meta.get('name_en','?')!s:45} {current_spec!r} → 'ORL'")
            fixed += 1

print(f"\n✅ {fixed} corriges, {reverted} annules (Charcot-Marie-Tooth etc.).")
