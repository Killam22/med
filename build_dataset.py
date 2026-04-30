# dataset/build_dataset.py — version complète avec MedQuAD + manuel

import pandas as pd
import json
import os
import xml.etree.ElementTree as ET
import argostranslate.translate

os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs("processed", exist_ok=True)

# ══════════════════════════════════════════════
# TRADUCTION HORS LIGNE
# ══════════════════════════════════════════════

def translate(text, to_lang):
    try:
        if not text or str(text).strip() == "":
            return ""
        result = argostranslate.translate.translate(str(text)[:300], "en", to_lang)
        return result
    except:
        return str(text)


# ══════════════════════════════════════════════
# SYMPTÔMES CLÉS PAR MALADIE — étendu à 120 maladies
# ══════════════════════════════════════════════

KEY_SYMPTOMS_MAP = {
    # Respiratoire
    "influenza":                    "fever cough fatigue body ache headache chills sore throat",
    "flu":                          "fever cough fatigue body ache headache chills sore throat",
    "common cold":                  "runny nose sore throat cough sneezing mild fever congestion",
    "pneumonia":                    "fever cough chest pain shortness breath fatigue chills",
    "asthma":                       "shortness breath wheezing chest tightness cough",
    "bronchitis":                   "cough mucus chest discomfort shortness breath fatigue fever",
    "tuberculosis":                 "cough blood weight loss night sweats fever fatigue",
    "covid-19":                     "fever cough shortness breath fatigue loss smell taste",
    "covid":                        "fever cough shortness breath fatigue loss smell taste",
    "sinusitis":                    "facial pain nasal congestion headache thick mucus fever",
    "tonsillitis":                  "sore throat fever swollen tonsils difficulty swallowing",
    "rhinitis":                     "runny nose sneezing nasal congestion itchy eyes",
    "laryngitis":                   "hoarse voice sore throat cough fever",
    "pleuritis":                    "chest pain shortness breath fever cough",
    "pulmonary embolism":           "sudden shortness breath chest pain rapid heartbeat leg swelling",
    "copd":                         "chronic cough shortness breath wheezing mucus",

    # Cardiaque
    "heart attack":                 "chest pain shortness breath nausea sweating arm pain jaw pain",
    "myocardial infarction":        "chest pain shortness breath nausea sweating arm pain jaw pain",
    "heart failure":                "shortness breath fatigue swollen legs rapid heartbeat",
    "angina":                       "chest pain pressure shortness breath nausea sweating",
    "arrhythmia":                   "palpitations irregular heartbeat dizziness shortness breath",
    "hypertension":                 "headache dizziness chest pain shortness breath blurred vision",
    "stroke":                       "sudden headache confusion weakness numbness face arm leg",
    "deep vein thrombosis":         "leg pain swelling redness warmth calf pain",
    "pericarditis":                 "chest pain fever shortness breath rapid heartbeat",
    "endocarditis":                 "fever chills fatigue joint pain heart murmur",

    # Digestif
    "gastroenteritis":              "nausea vomiting diarrhea stomach cramps fever",
    "appendicitis":                 "abdominal pain right side nausea vomiting fever",
    "hepatitis":                    "jaundice fatigue nausea abdominal pain dark urine",
    "gastritis":                    "stomach pain nausea vomiting bloating indigestion",
    "ulcer":                        "stomach pain burning nausea vomiting heartburn",
    "peptic ulcer":                 "stomach pain burning nausea vomiting heartburn",
    "pancreatitis":                 "abdominal pain nausea vomiting fever back pain",
    "cholecystitis":                "right upper abdominal pain nausea vomiting fever",
    "crohn":                        "abdominal pain diarrhea weight loss fatigue blood stool",
    "irritable bowel":              "abdominal pain bloating diarrhea constipation cramping",
    "celiac disease":               "diarrhea abdominal pain bloating weight loss fatigue",
    "cirrhosis":                    "jaundice abdominal swelling fatigue easy bruising",
    "colitis":                      "abdominal pain diarrhea blood stool cramping",
    "diverticulitis":               "left abdominal pain fever nausea constipation diarrhea",
    "food poisoning":               "nausea vomiting diarrhea stomach cramps fever",
    "gallstones":                   "right upper abdominal pain nausea vomiting after fatty meal",
    "hemorrhoids":                  "rectal bleeding pain itching discomfort",
    "reflux":                       "heartburn chest pain regurgitation difficulty swallowing",
    "gastroesophageal reflux":      "heartburn chest pain regurgitation difficulty swallowing",

    # Neurologique
    "migraine":                     "severe headache nausea vomiting light sensitivity throbbing",
    "epilepsy":                     "seizures convulsions loss consciousness muscle stiffness",
    "meningitis":                   "severe headache fever stiff neck light sensitivity vomiting",
    "parkinson":                    "tremor stiffness slow movement balance problems",
    "alzheimer":                    "memory loss confusion disorientation personality changes",
    "multiple sclerosis":           "numbness weakness vision problems balance fatigue",
    "vertigo":                      "dizziness spinning sensation nausea balance problems",
    "cluster headache":             "severe one-sided headache eye pain tearing nasal congestion",
    "tension headache":             "mild moderate headache pressure both sides neck pain",
    "bell palsy":                   "facial weakness drooping eye mouth difficulty closing eye",
    "carpal tunnel":                "hand numbness tingling weakness wrist pain",
    "sciatica":                     "lower back pain leg pain numbness tingling buttock",

    # Endocrinien
    "diabetes":                     "frequent urination thirst fatigue blurred vision slow healing",
    "diabetes mellitus":            "frequent urination thirst fatigue blurred vision slow healing",
    "hypothyroidism":               "fatigue weight gain cold sensitivity dry skin constipation",
    "hyperthyroidism":              "weight loss rapid heartbeat sweating anxiety tremor",
    "addison disease":              "fatigue weakness low blood pressure darkening skin",
    "cushing syndrome":             "weight gain round face high blood pressure stretch marks",
    "polycystic ovary":             "irregular periods weight gain acne excess hair",
    "gout":                         "sudden joint pain swelling redness warmth uric acid",

    # Dermatologique
    "psoriasis":                    "red patches scaly skin itching dry skin nail changes",
    "eczema":                       "itching red skin dry patches inflammation rash",
    "acne":                         "pimples blackheads whiteheads oily skin scarring",
    "urticaria":                    "hives itching red welts swelling skin",
    "allergy":                      "rash itching swelling sneezing runny nose",
    "allergic reaction":            "rash itching swelling sneezing runny nose",
    "chickenpox":                   "itchy blisters fever rash red spots",
    "varicella":                    "itchy blisters fever rash red spots",
    "shingles":                     "painful rash blisters burning one side body",
    "ringworm":                     "circular rash itching red border scaly patch",
    "rosacea":                      "facial redness flushing visible blood vessels bumps",
    "cellulitis":                   "red swollen warm skin pain fever",
    "measles":                      "fever rash runny nose cough red eyes spots mouth",
    "rubella":                      "mild fever rash swollen lymph nodes joint pain",

    # Musculo-squelettique
    "arthritis":                    "joint pain swelling stiffness reduced motion redness",
    "rheumatoid arthritis":         "joint pain swelling morning stiffness symmetric fatigue",
    "osteoarthritis":               "joint pain stiffness reduced motion cartilage loss",
    "back pain":                    "lower back pain stiffness muscle spasm radiating leg",
    "dorsalgia":                    "lower back pain stiffness muscle spasm radiating leg",
    "osteoporosis":                 "back pain height loss fractures stooped posture",
    "fibromyalgia":                 "widespread pain fatigue sleep problems tender points",
    "lupus":                        "joint pain rash fatigue fever hair loss",
    "tendinitis":                   "joint pain swelling tenderness movement difficulty",
    "bursitis":                     "joint pain swelling warmth limited movement",

    # Urinaire
    "urinary tract infection":      "burning urination frequent urge cloudy urine pelvic pain",
    "urinary tract":                "burning urination frequent urge cloudy urine pelvic pain",
    "kidney stones":                "severe back pain blood urine nausea vomiting fever",
    "urolithiasis":                 "severe back pain blood urine nausea vomiting fever",
    "kidney":                       "back pain swelling fatigue urination changes blood urine",
    "chronic kidney disease":       "fatigue swelling urination changes shortness breath nausea",
    "pyelonephritis":               "back pain fever chills nausea burning urination",
    "prostatitis":                  "pelvic pain burning urination frequent urge fever",
    "cystitis":                     "burning urination frequent urge pelvic pain cloudy urine",

    # Infectieux
    "malaria":                      "fever chills sweating headache nausea vomiting muscle pain",
    "dengue":                       "high fever severe headache joint pain rash bleeding",
    "typhoid":                      "sustained fever headache abdominal pain diarrhea weakness",
    "hiv":                          "fever fatigue swollen lymph nodes weight loss night sweats",
    "mononucleosis":                "fever sore throat swollen lymph nodes fatigue spleen",
    "otitis":                       "ear pain fever hearing loss fluid ear drainage",
    "conjunctivitis":               "red eyes discharge itching tearing light sensitivity",
    "sepsis":                       "fever rapid heartbeat rapid breathing confusion low blood pressure",
    "lyme disease":                 "bull's eye rash fever fatigue joint pain",

    # Psychiatrique
    "depression":                   "sadness hopelessness fatigue sleep problems appetite changes",
    "major depressive disorder":    "sadness hopelessness fatigue sleep problems appetite changes",
    "anxiety":                      "worry fear rapid heartbeat sweating restlessness",
    "anxiety disorder":             "worry fear rapid heartbeat sweating restlessness",
    "panic disorder":               "sudden intense fear chest pain rapid heartbeat shortness breath",
    "bipolar":                      "mood swings mania depression energy changes sleep",
    "schizophrenia":                "hallucinations delusions disorganized thinking",
    "ptsd":                         "flashbacks nightmares anxiety hypervigilance avoidance",
    "ocd":                          "obsessive thoughts compulsive behaviors anxiety rituals",
    "insomnia":                     "difficulty sleeping staying asleep fatigue daytime sleepiness",
    "adhd":                         "inattention hyperactivity impulsivity difficulty focusing",

    # Hématologique
    "anemia":                       "fatigue weakness pale skin shortness breath dizziness",
    "iron deficiency anemia":       "fatigue weakness pale skin cold hands brittle nails",
    "leukemia":                     "fatigue fever night sweats easy bleeding weight loss",
    "lymphoma":                     "swollen lymph nodes fatigue night sweats weight loss",
    "hemophilia":                   "excessive bleeding joint pain bruising prolonged bleeding",

    # Ophtalmologique
    "glaucoma":                     "vision loss eye pain halos around lights headache",
    "cataract":                     "blurred vision glare sensitivity faded colors",
    "macular degeneration":         "central vision loss blurred vision straight lines distorted",

    # ORL
    "hearing loss":                 "difficulty hearing muffled sounds ringing ears",
    "tinnitus":                     "ringing buzzing ears hearing difficulty",
}

DESCRIPTIONS_MAP = {
    "influenza":        "Viral infection affecting the respiratory system causing fever, cough, and body aches.",
    "common cold":      "Mild viral infection of the upper respiratory tract causing runny nose and sore throat.",
    "pneumonia":        "Lung infection causing inflammation of air sacs, leading to fever, cough, and breathing difficulty.",
    "asthma":           "Chronic respiratory disease causing airway inflammation and breathing difficulty.",
    "bronchitis":       "Inflammation of the bronchial tubes causing cough and mucus production.",
    "tuberculosis":     "Bacterial infection primarily affecting the lungs causing chronic cough and weight loss.",
    "hypertension":     "Chronic condition of elevated blood pressure that can lead to heart disease.",
    "diabetes":         "Metabolic disorder characterized by high blood sugar due to insulin problems.",
    "migraine":         "Neurological condition causing intense recurring headaches with nausea and light sensitivity.",
    "epilepsy":         "Neurological disorder causing recurrent seizures due to abnormal brain activity.",
    "gastroenteritis":  "Inflammation of stomach and intestines causing nausea, vomiting, and diarrhea.",
    "appendicitis":     "Inflammation of the appendix causing severe right-sided abdominal pain requiring surgery.",
    "hepatitis":        "Liver inflammation usually caused by viral infection, causing jaundice and fatigue.",
    "malaria":          "Parasitic infection transmitted by mosquitoes causing recurring fever and chills.",
    "dengue":           "Viral infection transmitted by mosquitoes causing high fever, severe headache, and joint pain.",
    "depression":       "Mental health disorder causing persistent sadness, hopelessness, and loss of interest.",
    "anxiety":          "Mental health disorder causing excessive worry, fear, and physical symptoms.",
    "arthritis":        "Joint inflammation causing pain, swelling, and reduced range of motion.",
    "urinary tract infection": "Bacterial infection of the urinary system causing burning urination.",
    "psoriasis":        "Chronic skin condition causing red, scaly patches on the skin surface.",
    "eczema":           "Inflammatory skin condition causing itchy, red, and dry skin patches.",
    "anemia":           "Condition with insufficient red blood cells to carry oxygen, causing fatigue.",
    "stroke":           "Medical emergency where blood supply to brain is blocked causing sudden neurological symptoms.",
    "meningitis":       "Inflammation of brain membranes causing severe headache, stiff neck, and fever.",
    "covid-19":         "Respiratory illness caused by SARS-CoV-2 causing fever, cough, and loss of smell.",
    "heart attack":     "Medical emergency where blood flow to heart is blocked causing chest pain and shortness of breath.",
    "parkinson":        "Progressive neurological disorder causing tremor, stiffness, and slow movement.",
    "alzheimer":        "Progressive brain disorder causing memory loss, confusion, and personality changes.",
    "lupus":            "Autoimmune disease causing joint pain, rash, and fatigue.",
    "diabetes mellitus":"Chronic metabolic disease characterized by high blood glucose levels.",
    "kidney stones":    "Hard deposits of minerals in the kidneys causing severe pain and blood in urine.",
}


# ══════════════════════════════════════════════
# UTILITAIRES
# ══════════════════════════════════════════════

def assign_specialist(name):
    n = name.lower()
    if any(k in n for k in ["heart","cardiac","hypertension","coronary","angina","arrhythmia","pericarditis","endocarditis"]):
        return "cardiologue"
    if any(k in n for k in ["skin","acne","fungal","psoriasis","eczema","ringworm","dermat","melanoma","rosacea","urticaria","cellulitis"]):
        return "dermatologue"
    if any(k in n for k in ["diabetes","thyroid","hormone","obesity","metabolic","adrenal","cushing","addison","polycystic"]):
        return "endocrinologue"
    if any(k in n for k in ["gastro","liver","hepatitis","stomach","bowel","jaundice","pancrea","ulcer","colon","appendic","celiac","crohn","gallstone","hemorrhoid","reflux","cirrhosis","colitis","diverticulitis"]):
        return "gastro-entérologue"
    if any(k in n for k in ["lung","pneumonia","tuberculosis","asthma","bronchitis","respiratory","copd","covid","pulmonary","pleuritis","sinusitis","laryngitis"]):
        return "pneumologue"
    if any(k in n for k in ["brain","migraine","paralysis","epilepsy","vertigo","neuro","alzheimer","parkinson","stroke","meningit","multiple sclerosis","bell palsy","carpal","sciatica","cluster headache"]):
        return "neurologue"
    if any(k in n for k in ["joint","arthritis","bone","spine","rheumat","gout","osteo","lupus","fibromyalgia","tendinitis","bursitis"]):
        return "rhumatologue"
    if any(k in n for k in ["kidney","urinary","bladder","renal","prostate","cystitis","pyelonephritis","urolithiasis"]):
        return "urologue"
    if any(k in n for k in ["allergy","dengue","malaria","typhoid","infection","hiv","aids","viral","bacterial","tonsil","covid","lyme","sepsis","mononucleosis","conjunctivitis"]):
        return "infectiologue"
    if any(k in n for k in ["anxiety","depression","mental","psychiatric","bipolar","schizo","ocd","ptsd","panic","insomnia","adhd"]):
        return "psychiatre"
    if any(k in n for k in ["cancer","tumor","lymphoma","leukemia","oncol"]):
        return "oncologue"
    if any(k in n for k in ["eye","vision","retina","glaucoma","cataract","macular"]):
        return "ophtalmologue"
    if any(k in n for k in ["ear","hearing","otitis","sinus","throat","tonsil","nasal","tinnitus"]):
        return "ORL"
    if any(k in n for k in ["blood","anemia","hemophilia","sickle","thalassemia","lymphoma","leukemia"]):
        return "hématologue"
    return "médecin_généraliste"


def assign_category(name):
    n = name.lower()
    if any(k in n for k in ["infection","fever","viral","typhoid","malaria","fungal","dengue","aids","hepatitis","hiv","covid","bacteria","tonsil","sinus","lyme","sepsis","mononucleosis"]):
        return "infectieux"
    if any(k in n for k in ["heart","hypertension","cardiac","coronary","angina","arrhythmia","pericarditis","stroke","thrombosis"]):
        return "cardiovasculaire"
    if any(k in n for k in ["diabetes","thyroid","hormone","obesity","metabolic","cushing","addison"]):
        return "endocrinien"
    if any(k in n for k in ["lung","asthma","pneumonia","bronchitis","tuberculosis","copd","covid","pulmonary","sinusitis","laryngitis"]):
        return "respiratoire"
    if any(k in n for k in ["gastro","liver","hepatitis","stomach","bowel","jaundice","pancrea","ulcer","appendic","celiac","crohn","gallstone","reflux","cirrhosis","colitis"]):
        return "digestif"
    if any(k in n for k in ["skin","acne","psoriasis","eczema","ringworm","dermat","urticaria","rosacea","cellulitis","chickenpox","measles"]):
        return "dermatologique"
    if any(k in n for k in ["brain","migraine","epilepsy","paralysis","vertigo","neuro","stroke","meningit","alzheimer","parkinson","sciatica","carpal"]):
        return "neurologique"
    if any(k in n for k in ["joint","arthritis","bone","spine","rheumat","gout","osteo","lupus","fibromyalgia","tendinitis"]):
        return "musculo-squelettique"
    if any(k in n for k in ["kidney","urinary","bladder","renal","prostate","cystitis"]):
        return "urinaire"
    if any(k in n for k in ["anxiety","depression","mental","psychiatric","bipolar","schizo","ptsd","ocd","insomnia","panic"]):
        return "psychiatrique"
    if any(k in n for k in ["cancer","tumor","lymphoma","leukemia"]):
        return "oncologique"
    if any(k in n for k in ["blood","anemia","hemophilia","sickle"]):
        return "hématologique"
    if any(k in n for k in ["eye","vision","retina","glaucoma","cataract"]):
        return "ophtalmologique"
    if any(k in n for k in ["ear","hearing","otitis","tinnitus"]):
        return "ORL"
    return "général"


def assign_urgency(name, severity_score):
    n = name.lower()
    if any(k in n for k in ["heart attack","myocardial","stroke","meningit","appendicit","pulmonary embolism","anaphylaxis","sepsis","eclampsia"]):
        return "urgent"
    if severity_score >= 5:
        return "urgent"
    elif severity_score >= 3:
        return "modéré"
    else:
        return "faible"


def get_key_symptoms(name_en, symptoms_en):
    name_lower = name_en.lower()
    # Cherche correspondance exacte d'abord
    for key, symptoms in KEY_SYMPTOMS_MAP.items():
        if key == name_lower:
            return symptoms
    # Puis correspondance partielle
    for key, symptoms in KEY_SYMPTOMS_MAP.items():
        if key in name_lower or name_lower in key:
            return symptoms
    # Fallback : prend les 8 premiers symptômes
    return " ".join(symptoms_en[:8])


def clean_symptom(s):
    return str(s).strip().replace("_", " ").replace("  ", " ").lower()


def merge_disease(existing, new_symptoms, new_description="", new_precautions=None):
    for s in new_symptoms:
        if s and s not in existing["symptoms_en"]:
            existing["symptoms_en"].append(s)
    if not existing.get("description_en") and new_description:
        existing["description_en"] = new_description
    if not existing.get("precautions_en") and new_precautions:
        existing["precautions_en"] = new_precautions
    return existing


# ══════════════════════════════════════════════
# SOURCE 0 — DATASET MANUEL (priorité maximale)
# ══════════════════════════════════════════════

def load_manual_dataset(diseases):
    print("\n📦 Source 0 — Dataset manuel (haute qualité)...")
    added = merged = 0
    try:
        with open("raw/manual/diseases_manual.json", "r", encoding="utf-8") as f:
            manual = json.load(f)

        for d in manual:
            name = d["name_en"]
            key  = name.lower()
            symptoms = d.get("symptoms_en", [])
            desc     = d.get("description_en", "")
            precs    = d.get("precautions_en", [])

            if key in diseases:
                diseases[key] = merge_disease(diseases[key], symptoms, desc, precs)
                diseases[key]["description_en"] = desc
                diseases[key]["precautions_en"] = precs
                diseases[key]["key_symptoms"]   = d.get("key_symptoms", "")
                diseases[key]["icd10_code"]     = d.get("icd10", "")
                diseases[key]["name_fr"]        = d.get("name_fr", "")
                diseases[key]["name_ar"]        = d.get("name_ar", "")
                diseases[key]["symptoms_fr"]    = d.get("symptoms_fr", [])
                diseases[key]["symptoms_ar"]    = d.get("symptoms_ar", [])
                diseases[key]["urgency"]        = d.get("urgency", "")
                diseases[key]["specialist"]     = d.get("specialist", "")
                diseases[key]["category"]       = d.get("category", "")
                merged += 1
            else:
                diseases[key] = {
                    "name_en":        name,
                    "name_fr":        d.get("name_fr", ""),
                    "name_ar":        d.get("name_ar", ""),
                    "symptoms_en":    symptoms,
                    "symptoms_fr":    d.get("symptoms_fr", []),
                    "symptoms_ar":    d.get("symptoms_ar", []),
                    "description_en": desc,
                    "description_fr": d.get("description_fr", ""),
                    "description_ar": d.get("description_ar", ""),
                    "precautions_en": precs,
                    "precautions_fr": d.get("precautions_fr", []),
                    "key_symptoms":   d.get("key_symptoms", ""),
                    "icd10_code":     d.get("icd10", ""),
                    "severity_score": float(d.get("severity", 3)),
                    "urgency":        d.get("urgency", "modéré"),
                    "specialist":     d.get("specialist", "médecin_généraliste"),
                    "category":       d.get("category", "général"),
                    "source":         "manual",
                }
                added += 1

        print(f"  ✅ {added} ajoutées, {merged} enrichies depuis dataset manuel")
    except Exception as e:
        print(f"  ⚠️ Erreur dataset manuel: {e}")
    return diseases


# ══════════════════════════════════════════════
# SOURCE 6 — MedQuAD (NIH officiel)
# ══════════════════════════════════════════════

def load_medquad(diseases):
    print("\n📦 Source 6 — MedQuAD (NIH officiel)...")

    relevant_folders = [
        "2_GARD_QA", "3_GHR_QA", "4_MPlus_Health_Topics_QA",
        "5_NIDDK_QA", "6_NINDS_QA", "8_NHLBI_QA_XML", "9_CDC_QA",
    ]

    base_path = "raw/medquad/MedQuAD-master"
    added = merged = skipped = 0

    for folder in relevant_folders:
        folder_path = os.path.join(base_path, folder)
        if not os.path.exists(folder_path):
            print(f"  ⚠️ Dossier manquant: {folder}")
            continue

        xml_files = [f for f in os.listdir(folder_path) if f.endswith(".xml")]
        print(f"  📁 {folder}: {len(xml_files)} fichiers")

        for xml_file in xml_files:
            try:
                tree = ET.parse(os.path.join(folder_path, xml_file))
                root = tree.getroot()

                focus = root.find("Focus")
                if focus is None or not focus.text:
                    continue

                disease_name = focus.text.strip()
                if not disease_name or len(disease_name) < 2:
                    continue

                symptoms    = []
                description = ""
                precautions = []

                for qa in root.findall(".//QAPair"):
                    question = qa.find("Question")
                    answer   = qa.find("Answer")
                    if question is None or answer is None:
                        continue

                    q_text = (question.text or "").lower()
                    a_text = answer.text or ""

                    if any(kw in q_text for kw in ["symptom", "sign", "what are the"]):
                        extracted = _extract_symptoms_from_text(a_text)
                        symptoms.extend(extracted)

                    if any(kw in q_text for kw in ["what is", "information about", "overview"]):
                        if not description and len(a_text) > 50:
                            description = a_text[:300].strip()

                    if any(kw in q_text for kw in ["prevent", "treatment", "management"]):
                        if not precautions and len(a_text) > 30:
                            precautions = [a_text[:150].strip()]

                symptoms = list(set([s for s in symptoms if s and len(s) > 3]))[:20]

                if not symptoms and not description:
                    skipped += 1
                    continue

                key = disease_name.lower()
                if key in diseases:
                    diseases[key] = merge_disease(diseases[key], symptoms, description, precautions)
                    merged += 1
                else:
                    diseases[key] = {
                        "name_en":        disease_name,
                        "symptoms_en":    symptoms,
                        "description_en": description,
                        "precautions_en": precautions,
                        "severity_score": 0,
                        "source":         "medquad"
                    }
                    added += 1

            except Exception:
                skipped += 1
                continue

    print(f"  ✅ {added} ajoutées, {merged} enrichies, {skipped} ignorées")
    return diseases


def _extract_symptoms_from_text(text: str) -> list:
    symptoms = []
    if not text:
        return symptoms

    medical_terms = [
        "fever", "cough", "pain", "fatigue", "nausea", "vomiting",
        "diarrhea", "headache", "dizziness", "weakness", "swelling",
        "rash", "itching", "bleeding", "shortness of breath",
        "chest pain", "abdominal pain", "back pain", "joint pain",
        "muscle pain", "weight loss", "weight gain", "appetite loss",
        "sweating", "chills", "tremor", "seizure", "confusion",
        "memory loss", "vision problems", "hearing loss", "numbness",
        "tingling", "constipation", "bloating", "heartburn", "jaundice",
        "dark urine", "frequent urination", "thirst", "anxiety",
        "depression", "insomnia", "night sweats", "palpitations",
        "sore throat", "runny nose", "congestion", "sneezing",
        "muscle aches", "stiff neck", "loss of appetite",
    ]

    text_lower = text.lower()
    for term in medical_terms:
        if term in text_lower:
            symptoms.append(term)

    stop_words = {
        "the", "and", "or", "of", "in", "is", "are", "may", "can",
        "that", "this", "with", "for", "not", "have", "has", "been",
        "also", "such", "when", "if", "it", "its", "a", "an",
        "include", "including", "following", "some", "other",
        "patient", "people", "person", "condition", "disease",
        "disorder", "syndrome", "common", "often", "usually"
    }

    lines = text.replace(" - ", "\n").replace("• ", "\n").split("\n")
    for line in lines:
        line = line.strip()
        words = line.split()
        if 1 <= len(words) <= 4:
            clean = clean_symptom(line)
            if clean and len(clean) > 3 and not any(w in stop_words for w in clean.split()):
                symptoms.append(clean)

    return symptoms[:15]


# ══════════════════════════════════════════════
# SOURCES KAGGLE
# ══════════════════════════════════════════════

def load_itachi():
    print("\n📦 Source 1 — itachi9604...")
    diseases = {}
    try:
        df      = pd.read_csv("raw/kaggle/dataset.csv")
        df_desc = pd.read_csv("raw/kaggle/symptom_Description.csv")
        df_prec = pd.read_csv("raw/kaggle/symptom_precaution.csv")
        df_sev  = pd.read_csv("raw/kaggle/Symptom-severity.csv")
        df_sev.columns = df_sev.columns.str.strip()
        df_sev["Symptom"] = df_sev["Symptom"].str.strip().str.replace("_", " ")
        sev_map = dict(zip(df_sev["Symptom"], df_sev["weight"]))

        for disease_name in df["Disease"].unique():
            rows = df[df["Disease"] == disease_name]
            symptoms = []
            for _, row in rows.iterrows():
                for col in row.index:
                    if col.startswith("Symptom") and pd.notna(row[col]):
                        s = clean_symptom(row[col])
                        if s and s not in symptoms:
                            symptoms.append(s)
            desc_row    = df_desc[df_desc["Disease"] == disease_name]
            description = desc_row["Description"].values[0] if len(desc_row) > 0 else ""
            prec_row    = df_prec[df_prec["Disease"] == disease_name]
            precautions = []
            if len(prec_row) > 0:
                for col in ["Precaution_1","Precaution_2","Precaution_3","Precaution_4"]:
                    if col in prec_row.columns:
                        val = prec_row[col].values[0]
                        if pd.notna(val):
                            precautions.append(str(val).replace("_", " "))
            scores = [sev_map.get(s, 0) for s in symptoms]
            avg = sum(scores) / len(scores) if scores else 0
            diseases[disease_name.lower()] = {
                "name_en": disease_name, "symptoms_en": symptoms,
                "description_en": str(description), "precautions_en": precautions,
                "severity_score": round(avg, 2), "source": "itachi9604"
            }
        print(f"  ✅ {len(diseases)} maladies chargées")
    except Exception as e:
        print(f"  ⚠️ Erreur: {e}")
    return diseases


def load_symptoms_to_diseases(diseases):
    print("\n📦 Source 2 — symptoms_to_diseases...")
    added = merged = 0
    try:
        df = pd.read_csv("raw/kaggle/symptoms_to_diseases/final_symptoms_to_disease.csv")
        disease_col = next((c for c in df.columns if "disease" in c.lower() or "label" in c.lower()), df.columns[-1])
        for _, row in df.drop_duplicates(subset=[disease_col]).iterrows():
            disease_name = str(row[disease_col]).strip()
            if not disease_name or disease_name == "nan": continue
            symptoms = []
            for col in df.columns:
                if col != disease_col:
                    val = row[col]
                    if pd.notna(val) and str(val).strip() not in ["0","nan","","False","false"]:
                        s = clean_symptom(col if str(val) in ["1","True","true"] else str(val))
                        if s and len(s) > 2 and s not in symptoms: symptoms.append(s)
            key = disease_name.lower()
            if key in diseases: diseases[key] = merge_disease(diseases[key], symptoms); merged += 1
            else: diseases[key] = {"name_en": disease_name, "symptoms_en": symptoms, "description_en": "", "precautions_en": [], "severity_score": 0, "source": "symptoms_to_diseases"}; added += 1
        print(f"  ✅ {added} ajoutées, {merged} fusionnées")
    except Exception as e: print(f"  ⚠️ Erreur: {e}")
    return diseases


def load_diseases261(diseases):
    print("\n📦 Source 3 — diseases261...")
    added = merged = 0
    try:
        df = pd.read_csv("raw/kaggle/diseases261/Final_Augmented_dataset_Diseases_and_Symptoms.csv", low_memory=False, nrows=5000)
        disease_col = next((c for c in df.columns if "disease" in c.lower() or "label" in c.lower()), df.columns[0])
        for _, row in df.drop_duplicates(subset=[disease_col]).iterrows():
            disease_name = str(row[disease_col]).strip()
            if not disease_name or disease_name == "nan": continue
            symptoms = []
            for col in df.columns:
                if col != disease_col:
                    val = row[col]
                    if pd.notna(val) and str(val).strip() not in ["0","nan","","False","false","No"]:
                        s = clean_symptom(col if str(val) in ["1","True","true","Yes"] else str(val))
                        if s and len(s) > 2 and s not in symptoms: symptoms.append(s)
            key = disease_name.lower()
            if key in diseases: diseases[key] = merge_disease(diseases[key], symptoms); merged += 1
            else: diseases[key] = {"name_en": disease_name, "symptoms_en": symptoms, "description_en": "", "precautions_en": [], "severity_score": 0, "source": "diseases261"}; added += 1
        print(f"  ✅ {added} ajoutées, {merged} fusionnées")
    except Exception as e: print(f"  ⚠️ Erreur: {e}")
    return diseases


def load_choong(diseases):
    print("\n📦 Source 4 — diseases_choong...")
    added = merged = 0
    try:
        df      = pd.read_csv("raw/kaggle/diseases_choong/DiseaseAndSymptoms.csv")
        df_prec = pd.read_csv("raw/kaggle/diseases_choong/Disease precaution.csv")
        prec_map = {}
        if "Disease" in df_prec.columns:
            for _, row in df_prec.iterrows():
                prec_map[str(row["Disease"]).strip().lower()] = [str(row[col]).strip().replace("_"," ") for col in df_prec.columns if "precaution" in col.lower() and pd.notna(row[col])]
        disease_col = next((c for c in df.columns if "disease" in c.lower()), df.columns[0])
        for _, row in df.drop_duplicates(subset=[disease_col]).iterrows():
            disease_name = str(row[disease_col]).strip()
            if not disease_name or disease_name == "nan": continue
            symptoms = []
            for col in df.columns:
                if col != disease_col:
                    val = row[col]
                    if pd.notna(val) and str(val).strip() not in ["0","nan",""]:
                        s = clean_symptom(col if str(val) in ["1","True","true"] else str(val))
                        if s and len(s) > 2 and s not in symptoms: symptoms.append(s)
            key = disease_name.lower()
            if key in diseases: diseases[key] = merge_disease(diseases[key], symptoms, "", prec_map.get(key,[])); merged += 1
            else: diseases[key] = {"name_en": disease_name, "symptoms_en": symptoms, "description_en": "", "precautions_en": prec_map.get(key,[]), "severity_score": 0, "source": "choong"}; added += 1
        print(f"  ✅ {added} ajoutées, {merged} fusionnées")
    except Exception as e: print(f"  ⚠️ Erreur: {e}")
    return diseases


def load_patient_profile(diseases):
    print("\n📦 Source 5 — patient_profile...")
    added = merged = 0
    try:
        df = pd.read_csv("raw/kaggle/patient_profile/Disease_symptom_and_patient_profile_dataset.csv")
        disease_col  = next((c for c in df.columns if "disease" in c.lower()), df.columns[0])
        symptom_cols = [c for c in df.columns if any(k in c.lower() for k in ["symptom","fever","cough","fatigue","pain","breath","nausea","headache"])]
        for _, row in df.drop_duplicates(subset=[disease_col]).iterrows():
            disease_name = str(row[disease_col]).strip()
            if not disease_name or disease_name == "nan": continue
            symptoms = []
            for col in symptom_cols:
                val = row[col]
                if pd.notna(val) and str(val).strip() not in ["0","nan","","No","no"]:
                    s = clean_symptom(col if str(val) in ["1","Yes","yes"] else str(val))
                    if s and len(s) > 2 and s not in symptoms: symptoms.append(s)
            key = disease_name.lower()
            if key in diseases: diseases[key] = merge_disease(diseases[key], symptoms); merged += 1
            else: diseases[key] = {"name_en": disease_name, "symptoms_en": symptoms, "description_en": "", "precautions_en": [], "severity_score": 0, "source": "patient_profile"}; added += 1
        print(f"  ✅ {added} ajoutées, {merged} fusionnées")
    except Exception as e: print(f"  ⚠️ Erreur: {e}")
    return diseases


def enrich_with_icd10(diseases):
    print("\n📦 Enrichissement ICD-10...")
    try:
        with open("raw/icd10/codes.json", "r", encoding="utf-8") as f:
            icd10 = json.load(f)
        icd10_map = {item["description"].lower(): item["code"] for item in icd10}
        matched = 0
        for disease in diseases.values():
            if disease.get("icd10_code"): continue
            name = disease["name_en"].lower()
            for desc, code in icd10_map.items():
                if any(word in desc for word in name.split() if len(word) > 4):
                    disease["icd10_code"] = code; matched += 1; break
        print(f"  ✅ {matched} maladies enrichies avec ICD-10")
    except Exception as e: print(f"  ⚠️ Erreur ICD-10: {e}")
    return diseases


# ══════════════════════════════════════════════
# JSON FINAL — FIX : index_text enrichi
# ══════════════════════════════════════════════

def build_final_json(diseases):
    print("\n📦 Construction JSON final...")
    final = []
    for i, (key, d) in enumerate(diseases.items()):
        name           = d["name_en"]
        clean_symptoms = list(set([s for s in d.get("symptoms_en", []) if s and len(s) > 2 and s != "nan"]))[:30]
        score          = d.get("severity_score", 0)
        urgency        = d.get("urgency") or assign_urgency(name, score)
        description    = d.get("description_en", "")
        if not description or description == "nan":
            description = DESCRIPTIONS_MAP.get(name.lower(), "")
        key_symp   = d.get("key_symptoms") or get_key_symptoms(name, clean_symptoms)
        specialist = d.get("specialist")  or assign_specialist(name)
        category   = d.get("category")   or assign_category(name)

        # FIX : index_text beaucoup plus riche — répète les key_symptoms
        # pour augmenter leur poids dans l'embedding
        index_text = (
            f"{name}. "
            f"{key_symp}. "                              # 1x key symptoms
            f"Symptoms: {', '.join(clean_symptoms[:12])}. "
            f"{key_symp}. "                              # 2x = poids double
            f"{description}"
        ).strip()

        final.append({
            "id":             f"D{i+1:04d}",
            "name_en":        name,
            "name_fr":        d.get("name_fr", ""),
            "name_ar":        d.get("name_ar", ""),
            "symptoms_en":    clean_symptoms,
            "symptoms_fr":    d.get("symptoms_fr", []),
            "symptoms_ar":    d.get("symptoms_ar", []),
            "key_symptoms":   key_symp,
            "index_text":     index_text,
            "description_en": description,
            "description_fr": d.get("description_fr", ""),
            "description_ar": d.get("description_ar", ""),
            "precautions_en": d.get("precautions_en", [])[:4],
            "precautions_fr": d.get("precautions_fr", []),
            "urgency":        urgency,
            "urgency_level":  urgency,
            "severity":       str(score),
            "severity_score": score,
            "specialist":     specialist,
            "category":       category,
            "icd10":          d.get("icd10_code", ""),
            "icd10_code":     d.get("icd10_code", ""),
            "source":         d.get("source", "mixed"),
        })

    priority = {"manual": 0, "itachi9604": 1, "medquad": 2, "choong": 3}
    final.sort(key=lambda x: priority.get(x["source"], 4))
    print(f"  ✅ {len(final)} maladies au total")
    return final


# ══════════════════════════════════════════════
# TRADUCTION
# ══════════════════════════════════════════════

def translate_diseases(diseases):
    print(f"\n🌍 Traduction de {len(diseases)} maladies...")
    for i, d in enumerate(diseases):
        if d.get("name_fr") and d["name_fr"] != d["name_en"]:
            continue
        print(f"  [{i+1}/{len(diseases)}] {d['name_en']}")
        try:
            d["name_fr"] = translate(d["name_en"], "fr")
            d["name_ar"] = translate(d["name_en"], "ar")
            if d.get("description_en"):
                d["description_fr"] = translate(d["description_en"][:300], "fr")
                d["description_ar"] = translate(d["description_en"][:300], "ar")
            if not d.get("symptoms_fr"):
                d["symptoms_fr"] = [translate(s, "fr") for s in d["symptoms_en"][:8]]
            if not d.get("symptoms_ar"):
                d["symptoms_ar"] = [translate(s, "ar") for s in d["symptoms_en"][:8]]
            if not d.get("precautions_fr"):
                d["precautions_fr"] = [translate(p, "fr") for p in d["precautions_en"][:4]]
            if (i + 1) % 100 == 0:
                with open("processed/diseases_temp.json", "w", encoding="utf-8") as f:
                    json.dump(diseases[:i+1], f, ensure_ascii=False, indent=2)
                print(f"  💾 Sauvegarde: {i+1} maladies traduites")
        except Exception as e:
            d["name_fr"] = d.get("name_fr") or d["name_en"]
            d["name_ar"] = d.get("name_ar") or d["name_en"]
    return diseases


# ══════════════════════════════════════════════
# SPÉCIALISTES
# ══════════════════════════════════════════════

def build_specialists():
    print("\n📦 Spécialités médicales...")
    specialists = [
        {"id": "S001", "specialty_fr": "Médecin généraliste", "specialty_ar": "طبيب عام",                    "specialty_en": "General Practitioner",           "categories": ["général","infectieux"],          "urgency_compatible": ["faible","modéré"]},
        {"id": "S002", "specialty_fr": "Cardiologue",          "specialty_ar": "طبيب القلب",                  "specialty_en": "Cardiologist",                    "categories": ["cardiovasculaire"],              "urgency_compatible": ["modéré","urgent"]},
        {"id": "S003", "specialty_fr": "Dermatologue",         "specialty_ar": "طبيب الجلدية",                "specialty_en": "Dermatologist",                   "categories": ["dermatologique"],                "urgency_compatible": ["faible","modéré"]},
        {"id": "S004", "specialty_fr": "Gastro-entérologue",   "specialty_ar": "طبيب الجهاز الهضمي",          "specialty_en": "Gastroenterologist",              "categories": ["digestif"],                      "urgency_compatible": ["modéré","urgent"]},
        {"id": "S005", "specialty_fr": "Pneumologue",          "specialty_ar": "طبيب الرئة",                  "specialty_en": "Pulmonologist",                   "categories": ["respiratoire"],                  "urgency_compatible": ["modéré","urgent"]},
        {"id": "S006", "specialty_fr": "Endocrinologue",       "specialty_ar": "طبيب الغدد الصماء",           "specialty_en": "Endocrinologist",                 "categories": ["endocrinien"],                   "urgency_compatible": ["faible","modéré"]},
        {"id": "S007", "specialty_fr": "Neurologue",           "specialty_ar": "طبيب الأعصاب",                "specialty_en": "Neurologist",                     "categories": ["neurologique"],                  "urgency_compatible": ["modéré","urgent"]},
        {"id": "S008", "specialty_fr": "Rhumatologue",         "specialty_ar": "طبيب الروماتيزم",             "specialty_en": "Rheumatologist",                  "categories": ["musculo-squelettique"],          "urgency_compatible": ["faible","modéré"]},
        {"id": "S009", "specialty_fr": "Urologue",             "specialty_ar": "طبيب المسالك البولية",        "specialty_en": "Urologist",                       "categories": ["urinaire"],                      "urgency_compatible": ["modéré","urgent"]},
        {"id": "S010", "specialty_fr": "Infectiologue",        "specialty_ar": "طبيب الأمراض المعدية",        "specialty_en": "Infectious Disease Specialist",   "categories": ["infectieux"],                    "urgency_compatible": ["modéré","urgent"]},
        {"id": "S011", "specialty_fr": "Psychiatre",           "specialty_ar": "طبيب نفسي",                   "specialty_en": "Psychiatrist",                    "categories": ["psychiatrique"],                 "urgency_compatible": ["faible","modéré","urgent"]},
        {"id": "S012", "specialty_fr": "Oncologue",            "specialty_ar": "طبيب الأورام",                "specialty_en": "Oncologist",                      "categories": ["oncologique"],                   "urgency_compatible": ["urgent"]},
        {"id": "S013", "specialty_fr": "Ophtalmologue",        "specialty_ar": "طبيب العيون",                 "specialty_en": "Ophthalmologist",                 "categories": ["ophtalmologique"],               "urgency_compatible": ["faible","modéré"]},
        {"id": "S014", "specialty_fr": "ORL",                  "specialty_ar": "طبيب الأذن والأنف والحنجرة", "specialty_en": "ENT Specialist",                  "categories": ["ORL"],                           "urgency_compatible": ["faible","modéré"]},
        {"id": "S015", "specialty_fr": "Hématologue",          "specialty_ar": "طبيب أمراض الدم",             "specialty_en": "Hematologist",                    "categories": ["hématologique"],                 "urgency_compatible": ["modéré","urgent"]},
    ]
    with open("processed/specialists.json", "w", encoding="utf-8") as f:
        json.dump(specialists, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {len(specialists)} spécialités sauvegardées")


def build_symptoms_mapping(diseases):
    print("\n📦 Mapping symptômes...")
    mapping = {}
    for d in diseases:
        for symptom in d["symptoms_en"]:
            key = symptom.lower().replace(" ", "_")
            if key not in mapping: mapping[key] = []
            if d["id"] not in mapping[key]: mapping[key].append(d["id"])
    with open("processed/symptoms_mapping.json", "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {len(mapping)} symptômes mappés")


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("   MEDICAL SMART APP — Pipeline Dataset Complet")
    print("   Sources: Manuel + 5x Kaggle + MedQuAD NIH")
    print("=" * 60)

    diseases = load_itachi()
    diseases = load_symptoms_to_diseases(diseases)
    diseases = load_diseases261(diseases)
    diseases = load_choong(diseases)
    diseases = load_patient_profile(diseases)
    diseases = load_medquad(diseases)
    diseases = load_manual_dataset(diseases)
    diseases = enrich_with_icd10(diseases)

    final_diseases = build_final_json(diseases)
    final_diseases = translate_diseases(final_diseases)

    with open("processed/diseases.json", "w", encoding="utf-8") as f:
        json.dump(final_diseases, f, ensure_ascii=False, indent=2)
    print(f"\n✅ diseases.json — {len(final_diseases)} maladies")

    build_specialists()
    build_symptoms_mapping(final_diseases)

    print("\n" + "=" * 60)
    print("✅ DATASET COMPLET dans dataset/processed/")
    print(f"   diseases.json          — {len(final_diseases)} maladies")
    print("   specialists.json       — 15 spécialités")
    print("   symptoms_mapping.json  — symptômes mappés")
    print("=" * 60)