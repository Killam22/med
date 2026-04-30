# training/ingest_to_chroma.py
import json
import os
import chromadb
from sentence_transformers import SentenceTransformer

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 65)
print("   MEDICAL SMART APP — Ingestion 2 Collections Chroma")
print("   multilingual-e5-large + key symptoms FR+AR")
print("=" * 65)

DATASET_PATH = r"C:\Users\HP\Desktop\ai_bot\dataset\processed\diseases_v4.json"
CHROMA_PATH       = r"C:\Users\HP\Desktop\ai_bot\chroma_db"
COLLECTION_COMMON = "medical_common"
COLLECTION_RARE   = "medical_rare"
MODEL_NAME = "pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb"

# ══════════════════════════════════════════════════════════
# KEY SYMPTOMS MULTILINGUES
# ══════════════════════════════════════════════════════════

KEY_SYMPTOMS_MAP_FR = {
    "heart attack":            "douleur poitrine bras gauche sueurs nausées essoufflement",
    "myocardial infarction":   "douleur poitrine bras gauche sueurs nausées infarctus",
    "meningitis":              "raideur nuque fièvre maux de tête photophobie vomissements",
    "influenza":               "fièvre toux sèche fatigue courbatures maux de tête frissons",
    "flu":                     "fièvre toux sèche fatigue courbatures maux de tête frissons",
    "covid-19":                "fièvre toux perte odorat goût fatigue essoufflement",
    "covid":                   "fièvre toux perte odorat goût fatigue essoufflement",
    "tuberculosis":            "toux chronique sueurs nocturnes perte de poids fièvre fatigue",
    "diabetes":                "soif excessive urination fréquente fatigue vision floue",
    "diabetes mellitus":       "soif excessive urination fréquente fatigue vision floue",
    "diabetes type 2":         "soif excessive urination fréquente fatigue vision floue",
    "appendicitis":            "douleur abdominale droite nausée fièvre vomissements",
    "gastroenteritis":         "diarrhée vomissements crampes abdominales fièvre nausée",
    "gastritis":               "douleur estomac nausée brûlures reflux douleur après repas",
    "migraine":                "maux de tête pulsatile nausée sensibilité lumière son",
    "parkinson":               "tremblements rigidité lenteur instabilité posturale",
    "parkinson disease":       "tremblements rigidité lenteur instabilité posturale",
    "pneumonia":               "fièvre toux douleur poitrine essoufflement frissons",
    "asthma":                  "essoufflement sifflement oppression poitrine toux",
    "hypertension":            "maux de tête vertiges douleur poitrine essoufflement",
    "depression":              "tristesse fatigue perte intérêt insomnie appétit",
    "anxiety":                 "anxiété palpitations sueurs peur insomnie tension",
    "stroke":                  "paralysie soudaine confusion perte parole maux de tête",
    "kidney stones":           "douleur lombaire intense sang urine nausée fièvre",
    "urinary tract infection": "brûlure miction urination fréquente urine trouble",
    "hepatitis":               "jaunisse fatigue nausée douleur abdominale urine foncée",
    "arthritis":               "douleur articulaire gonflement raideur matinale",
    "anemia":                  "fatigue faiblesse peau pâle essoufflement vertiges",
    "heart failure":           "essoufflement fatigue jambes gonflées palpitations",
    "bronchitis":              "toux mucus essoufflement fatigue fièvre",
    "sinusitis":               "douleur faciale congestion nasale maux de tête mucus",
    "otitis":                  "douleur oreille fièvre perte audition",
    "conjunctivitis":          "yeux rouges décharge larmoiement sensibilité lumière",
    "chickenpox":              "vésicules démangeaisons fièvre éruption cutanée",
    "malaria":                 "fièvre cyclique frissons sueurs maux de tête nausée",
    "dengue":                  "fièvre intense maux de tête douleurs articulaires éruption",
    "psoriasis":               "plaques rouges squameuses démangeaisons peau sèche",
    "eczema":                  "démangeaisons peau rouge sèche inflammation éruption",
    "lupus":                   "éruption papillon douleurs articulaires fatigue fièvre",
    "epilepsy":                "convulsions perte conscience rigidité musculaire",
    "alzheimer":               "perte mémoire confusion désorientation changements personnalité",
    "hypothyroidism":          "fatigue prise de poids froid peau sèche constipation",
    "hyperthyroidism":         "perte de poids palpitations transpiration anxiété",
    "pancreatitis":            "douleur abdominale sévère nausée vomissement fièvre",
}

KEY_SYMPTOMS_MAP_AR = {
    "heart attack":            "ألم في الصدر ألم في الذراع اليسرى تعرق غثيان ضيق في التنفس",
    "myocardial infarction":   "ألم صدري شديد ألم ذراع يسرى تعرق بارد ضيق تنفس",
    "meningitis":              "تيبس الرقبة حمى صداع شديد حساسية للضوء قيء",
    "influenza":               "حمى سعال جاف تعب آلام جسدية صداع قشعريرة",
    "flu":                     "حمى سعال جاف تعب آلام جسدية صداع قشعريرة",
    "covid-19":                "حمى سعال فقدان الشم والتذوق تعب ضيق تنفس",
    "covid":                   "حمى سعال فقدان الشم والتذوق تعب ضيق تنفس",
    "tuberculosis":            "سعال مزمن تعرق ليلي فقدان وزن حمى إرهاق",
    "diabetes":                "عطش شديد كثرة التبول تعب رؤية مشوشة",
    "diabetes mellitus":       "عطش شديد كثرة التبول تعب رؤية مشوشة",
    "diabetes type 2":         "عطش شديد كثرة التبول تعب رؤية مشوشة إرهاق",
    "appendicitis":            "ألم بطن أيمن غثيان حمى قيء",
    "gastroenteritis":         "إسهال قيء تقلصات بطنية حمى غثيان",
    "gastritis":               "ألم في المعدة غثيان حرقة ارتجاع حمض ألم بعد الأكل",
    "migraine":                "صداع نابض غثيان حساسية للضوء والصوت",
    "parkinson":               "رعشة تصلب بطء الحركة عدم الاتزان",
    "parkinson disease":       "رعشة تصلب بطء الحركة عدم الاتزان",
    "pneumonia":               "حمى سعال ألم صدري ضيق تنفس قشعريرة",
    "asthma":                  "ضيق تنفس صفير صدر ضيق سعال",
    "hypertension":            "صداع دوار ألم صدري ضيق تنفس",
    "depression":              "حزن تعب فقدان اهتمام أرق شهية",
    "anxiety":                 "قلق خفقان تعرق خوف أرق توتر",
    "stroke":                  "شلل مفاجئ ارتباك فقدان كلام صداع",
    "kidney stones":           "ألم ظهر شديد دم في البول غثيان حمى",
    "urinary tract infection": "حرقة تبول كثرة تبول بول معكر",
    "hepatitis":               "يرقان تعب غثيان ألم بطن بول داكن",
    "arthritis":               "ألم مفاصل تورم تصلب صباحي",
    "anemia":                  "تعب ضعف شحوب ضيق تنفس دوار",
    "heart failure":           "ضيق تنفس تعب تورم ساقين خفقان",
    "bronchitis":              "سعال مخاط ضيق تنفس تعب حمى",
    "sinusitis":               "ألم وجه احتقان أنف صداع مخاط",
    "chickenpox":              "حويصلات حكة حمى طفح جلدي",
    "malaria":                 "حمى دورية قشعريرة تعرق صداع غثيان",
    "dengue":                  "حمى شديدة صداع آلام مفاصل طفح",
    "psoriasis":               "بقع حمراء قشرية حكة جلد جاف",
    "eczema":                  "حكة جلد أحمر جاف التهاب طفح",
    "lupus":                   "طفح فراشة آلام مفاصل تعب حمى",
    "epilepsy":                "تشنجات فقدان وعي تصلب عضلي",
    "alzheimer":               "فقدان ذاكرة ارتباك تشوش تغيير شخصية",
    "hypothyroidism":          "تعب زيادة وزن برد جلد جاف إمساك",
    "hyperthyroidism":         "فقدان وزن خفقان تعرق قلق",
    "pancreatitis":            "ألم بطن شديد غثيان قيء حمى",
    "malaria":                 "حمى دورية قشعريرة تعرق ألم رأس",
}

# ══════════════════════════════════════════════════════════
# WHITELIST MALADIES COMMUNES
# ══════════════════════════════════════════════════════════

COMMON_WHITELIST = {
    "influenza","grippe","flu","common cold","rhinopharyngite","rhume",
    "pneumonia","pneumonie","asthma","asthme","bronchitis","bronchite",
    "tuberculosis","tuberculose","covid","coronavirus","sinusitis","sinusite",
    "tonsillitis","amygdalite","laryngitis","pharyngitis","copd",
    "hypertension","heart attack","infarctus","heart failure","insuffisance cardiaque",
    "angina","arrhythmia","stroke","avc","atherosclerosis","cholesterol",
    "gastroenteritis","gastro","appendicitis","appendicite","gastritis","gastrite",
    "hepatitis","hépatite","pancreatitis","pancréatite","ulcer","ulcère",
    "constipation","diarrhea","irritable bowel","crohn","colitis","jaundice",
    "celiac","coeliac","maladie coeliaque",
    "migraine","epilepsy","épilepsie","meningitis","méningite",
    "parkinson","alzheimer","multiple sclerosis","sclérose en plaques",
    "vertigo","vertige","stroke","als","amyotrophic lateral sclerosis",
    "malaria","paludisme","dengue","typhoid","typhoïde","hiv","aids",
    "chickenpox","varicelle","measles","rougeole","rabies","tetanus",
    "lyme","salmonella","cholera","covid-19",
    "psoriasis","eczema","acne","acné","ringworm","urticaria","dermatitis",
    "rosacea","vitiligo","melanoma",
    "diabetes","diabète","hypothyroidism","hypothyroïdie",
    "hyperthyroidism","hyperthyroïdie","obesity","obésité",
    "diabetes insipidus","cushing","addison",
    "depression","dépression","anxiety","anxiété","bipolar","bipolaire",
    "schizophrenia","ocd","ptsd","insomnia","eating disorder",
    "panic disorder","phobia","adhd","autism","anorexia","bulimia",
    "arthritis","arthrite","gout","goutte","osteoporosis","ostéoporose",
    "back pain","fibromyalgia","fibromyalgie","tendinitis","lupus",
    "scleroderma","myasthenia","sjogren","polymyositis",
    "urinary tract infection","kidney stones","calculs rénaux",
    "prostatitis","cystitis","nephritis","kidney disease",
    "anemia","anémie","leukemia","lymphoma","hemophilia","thalassemia",
    "sickle cell","thrombosis",
    "breast cancer","lung cancer","colon cancer","prostate cancer",
    "skin cancer","cervical cancer",
    "glaucoma","cataract","conjunctivitis","conjonctivite",
    "otitis","otite","hearing loss","tinnitus",
    "lupus erythematosus","systemic sclerosis","myasthenia gravis",
    "sjogren syndrome","celiac disease","crohn disease",
    "ulcerative colitis","hemophilia","thalassemia","wilson disease",
    "marfan","ehlers-danlos","guillain-barre","tourette","huntington",
    "cystic fibrosis","bipolar disorder","obsessive compulsive",
    "post traumatic","attention deficit","autism spectrum",
    "myocardial infarction","cardiac arrest","heart disease",
}

RARE_KEYWORDS = [
    "syndrome","dysplasia","dystrophy","dysgenesis","dysmorphia",
    "type 1","type 2","type 3","type a","type b","type c","type d",
    "autosomal","hereditary","congenital","familial","x-linked",
    "recessive","dominant","chromosom","malformation",
]


def is_common(disease: dict) -> bool:
    name   = disease.get("name_en", "").lower()
    source = disease.get("source", "")
    syms   = disease.get("symptoms_en", [])

    if source == "manual":
        return True

    for w in COMMON_WHITELIST:
        if w in name:
            return True

    if len(syms) < 4:
        return False

    rare_count = sum(1 for kw in RARE_KEYWORDS if kw in name)
    if rare_count >= 2:
        return False
    if rare_count == 1 and not disease.get("description_en", ""):
        return False

    return True


def build_document(disease: dict) -> str:
    name_en  = disease.get("name_en", "")
    name_fr  = disease.get("name_fr", "") or name_en
    name_ar  = disease.get("name_ar", "") or ""
    syms_en  = disease.get("symptoms_en", [])
    syms_fr  = disease.get("symptoms_fr", [])
    syms_ar  = disease.get("symptoms_ar", [])
    key_en   = disease.get("key_symptoms", "") or ", ".join(syms_en[:8])
    key_fr   = KEY_SYMPTOMS_MAP_FR.get(name_en.lower(), "") or ", ".join(syms_fr[:8])
    key_ar   = KEY_SYMPTOMS_MAP_AR.get(name_en.lower(), "") or ", ".join(syms_ar[:8])
    desc     = disease.get("description_en", "")[:200]
    urgency  = disease.get("urgency", "")
    spec     = disease.get("specialist", "")
    cat      = disease.get("category", "")

    # Répète key symptoms 3x pour augmenter leur poids dans l'embedding
    content = (
        f"DISEASE: {name_en} | {name_fr} | {name_ar}\n"
        f"KEY SYMPTOMS EN: {key_en}\n"
        f"KEY SYMPTOMS EN: {key_en}\n"
        f"KEY SYMPTOMS FR: {key_fr}\n"
        f"KEY SYMPTOMS FR: {key_fr}\n"
        f"KEY SYMPTOMS AR: {key_ar}\n"
        f"KEY SYMPTOMS AR: {key_ar}\n"
        f"ALL SYMPTOMS EN: {', '.join(syms_en[:15])}\n"
        f"ALL SYMPTOMS FR: {', '.join(syms_fr[:10])}\n"
        f"ALL SYMPTOMS AR: {', '.join(syms_ar[:10])}\n"
        f"DESCRIPTION: {desc}\n"
        f"SPECIALIST: {spec} | CATEGORY: {cat} | URGENCY: {urgency}"
    )
    # Préfixe requis par multilingual-e5-large pour les documents
    return f"passage: {content}"


def build_meta(disease: dict) -> dict:
    return {
        "name_en":      disease.get("name_en", ""),
        "name_fr":      disease.get("name_fr", ""),
        "name_ar":      disease.get("name_ar", ""),
        "specialist":   disease.get("specialist", ""),
        "category":     disease.get("category", ""),
        "urgency":      disease.get("urgency", disease.get("urgency_level", "")),
        "icd10":        disease.get("icd10", disease.get("icd10_code", "")),
        "severity":     str(disease.get("severity_score", 0)),
        "key_symptoms": disease.get("key_symptoms", ", ".join(disease.get("symptoms_en", [])[:8])),
        "source":       disease.get("source", "unknown"),
        "is_rare":      "false" if is_common(disease) else "true",
    }


def ingest(collection, diseases_list, model, label):
    BATCH = 16  # batch plus petit pour multilingual-e5-large (modèle plus lourd)
    total = 0
    for i in range(0, len(diseases_list), BATCH):
        batch = diseases_list[i:i+BATCH]
        docs, ids, metas = [], [], []
        for d in batch:
            try:
                docs.append(build_document(d))
                ids.append(d["id"])
                metas.append(build_meta(d))
            except:
                continue
        if not docs:
            continue
        try:
            embs = model.encode(
                docs,
                normalize_embeddings=True,
                show_progress_bar=False
            ).tolist()
            collection.add(documents=docs, embeddings=embs, ids=ids, metadatas=metas)
            total += len(batch)
            print(f"  [{label}] [{total}/{len(diseases_list)}] ✅")
        except Exception as e:
            print(f"  [{label}] ❌ {e}")
    return total


# ── Chargement modèle ─────────────────────────────────────
print(f"\n📦 Chargement {MODEL_NAME}...")
model = SentenceTransformer(MODEL_NAME)
print(f"  ✅ Modèle chargé — dim: {model.get_sentence_embedding_dimension()}")

# ── Chargement dataset ────────────────────────────────────
print("\n📦 Chargement dataset...")
with open(DATASET_PATH, "r", encoding="utf-8") as f:
    diseases = json.load(f)
print(f"  ✅ {len(diseases)} maladies chargées")

# ── Séparation common/rare ────────────────────────────────
common = [d for d in diseases if is_common(d)]
rare   = [d for d in diseases if not is_common(d)]
print(f"\n📊 Répartition :")
print(f"  Communes : {len(common)}")
print(f"  Rares    : {len(rare)}")

# ── Vérification maladies importantes ────────────────────
important = ["heart attack", "meningitis", "influenza", "covid", "tuberculosis",
             "diabetes", "appendicitis", "migraine", "parkinson", "pneumonia"]
common_names = {d["name_en"].lower() for d in common}
print("\n📋 Vérification maladies critiques dans common :")
for name in important:
    found = any(name in n for n in common_names)
    print(f"  {'✅' if found else '❌'} {name}")

# ── Chroma ────────────────────────────────────────────────
print("\n📦 Initialisation Chroma...")
os.makedirs(CHROMA_PATH, exist_ok=True)
client = chromadb.PersistentClient(path=CHROMA_PATH)

for name in [COLLECTION_COMMON, COLLECTION_RARE]:
    try:
        client.delete_collection(name)
        print(f"  🗑️ {name} supprimée")
    except:
        pass

# ip = inner product — optimal pour multilingual-e5-large avec normalize=True
col_c = client.create_collection(name=COLLECTION_COMMON, metadata={"hnsw:space": "cosine"})
col_r = client.create_collection(name=COLLECTION_RARE,   metadata={"hnsw:space": "cosine"})
print("  ✅ 2 collections créées (espace: ip)")

# ── Ingestion ─────────────────────────────────────────────
print(f"\n📦 Ingestion maladies communes ({len(common)})...")
ingest(col_c, common, model, "COMMON")

print(f"\n📦 Ingestion maladies rares ({len(rare)})...")
ingest(col_r, rare, model, "RARE")

print("\n" + "=" * 65)
print("✅ INGESTION TERMINÉE")
print(f"   medical_common : {col_c.count()} maladies")
print(f"   medical_rare   : {col_r.count()} maladies")
print(f"   Modèle         : {MODEL_NAME}")
print(f"   Espace         : inner product (ip)")
print("=" * 65)