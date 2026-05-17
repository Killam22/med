"""
Remplit le stock de la Pharmacie El Shifa (Mohamed Cherif) avec des médicaments réalistes.
Lancer : python manage.py shell -c "exec(open('scripts/fill_pharmacy_stock.py', encoding='utf-8').read())"
"""
from datetime import date
from medications.models import Medication
from pharmacy.models import Pharmacy, PharmacyStock

# ─── Récupérer la pharmacie ───────────────────────────────────────────────────
from django.contrib.auth import get_user_model
User = get_user_model()

pharmacy = None
try:
    u = User.objects.get(email='pharmacie.elshifa@demo.com')
    pharmacist = u.pharmacist_profile
    try:
        pharmacy = pharmacist.pharmacy
    except Exception:
        # La pharmacie n'existe pas encore, on la crée
        pharmacy = Pharmacy.objects.create(
            pharmacist=pharmacist,
            name='Pharmacie El Shifa',
            pharm_address='8 Rue Hassiba Ben Bouali',
            pharm_city='Alger Centre',
            pharm_phone='0555345679',
            agreement_number='AGR-DEMO-ELSHIFA-2025',
        )
        print(f"✅ Pharmacie créée : {pharmacy.name}")
    print(f"✅ Pharmacie trouvée : {pharmacy.name} ({pharmacy.pharm_city})")
except User.DoesNotExist:
    print("❌ Compte pharmacie.elshifa@demo.com introuvable. Lancez d'abord create_demo_accounts.py")
    raise SystemExit
except Exception as e:
    print(f"❌ Erreur : {e}")
    raise SystemExit


# ─── Catalogue de médicaments ─────────────────────────────────────────────────
# (name, molecule, category, form, dosage_forms, price_dzd, cnas_covered, requires_presc, manufacturer)
CATALOG = [
    # ── CARDIOLOGIE ────────────────────────────────────────────────────────────
    ("Amlodipine Biogaran 5mg",    "Amlodipine",         "cardio",     "Comprimé",     ["5mg"],         180.00, True,  True,  "Biogaran"),
    ("Amlodipine Biogaran 10mg",   "Amlodipine",         "cardio",     "Comprimé",     ["10mg"],        240.00, True,  True,  "Biogaran"),
    ("Lisinopril EG 10mg",         "Lisinopril",         "cardio",     "Comprimé",     ["5mg","10mg"],  195.00, True,  True,  "EG Pharma"),
    ("Losartan Teva 50mg",         "Losartan potassique","cardio",     "Comprimé",     ["50mg","100mg"],220.00, True,  True,  "Teva"),
    ("Ramipril Sandoz 5mg",        "Ramipril",           "cardio",     "Comprimé",     ["2.5mg","5mg"], 210.00, True,  True,  "Sandoz"),
    ("Aténolol Pharmos 50mg",      "Aténolol",           "cardio",     "Comprimé",     ["50mg","100mg"],185.00, True,  True,  "Pharmos"),
    ("Furosémide Générique 40mg",  "Furosémide",         "cardio",     "Comprimé",     ["40mg"],        120.00, True,  True,  "Générique"),
    ("Spironolactone EG 25mg",     "Spironolactone",     "cardio",     "Comprimé",     ["25mg","50mg"], 310.00, True,  True,  "EG Pharma"),
    ("Trinitrine Spray",           "Trinitrate de glycéryle","cardio", "Spray sublingual",["0.3mg"],    450.00, True,  True,  "Solvay Pharma"),
    ("Aspirine Cardio 100mg",      "Acide acétylsalicylique","cardio", "Comprimé",     ["100mg"],        95.00, True,  True,  "Bayer"),
    ("Atorvastatine Mylan 20mg",   "Atorvastatine calcique","cardio",  "Comprimé",     ["10mg","20mg","40mg"],280.00,True,True,"Mylan"),
    ("Oméga-3 Pharmos 1g",         "Acides gras oméga-3","cardio",    "Capsule",       ["1g"],          390.00, False, False, "Pharmos"),
    ("Valsartan Teva 80mg",        "Valsartan",          "cardio",     "Comprimé",     ["80mg","160mg"],260.00, True,  True,  "Teva"),

    # ── DIABÉTOLOGIE ──────────────────────────────────────────────────────────
    ("Metformine EG 500mg",        "Metformine HCl",     "diabetes",   "Comprimé",     ["500mg"],       115.00, True,  True,  "EG Pharma"),
    ("Metformine EG 1000mg",       "Metformine HCl",     "diabetes",   "Comprimé",     ["1000mg"],      175.00, True,  True,  "EG Pharma"),
    ("Glucophage 500mg",           "Metformine HCl",     "diabetes",   "Comprimé",     ["500mg","850mg"],180.00,True,  True,  "Merck"),
    ("Glucophage XR 1000mg",       "Metformine HCl",     "diabetes",   "Comprimé LP",  ["1000mg"],      220.00, True,  True,  "Merck"),
    ("Glimépéride Sandoz 2mg",     "Glimépéride",        "diabetes",   "Comprimé",     ["1mg","2mg","4mg"],195.00,True,True,  "Sandoz"),
    ("Insuline Actrapid FlexPen",  "Insuline humaine",   "diabetes",   "Solution injectable",["100UI/mL"],890.00,True,True, "Novo Nordisk"),
    ("Insuline Lantus SoloStar",   "Insuline glargine",  "diabetes",   "Solution injectable",["100UI/mL"],1250.00,True,True,"Sanofi"),
    ("Bandelettes Glycémiques x50","—",                  "diabetes",   "Consommable",  [],              650.00, False, False, "One Touch"),

    # ── ANTIBIOTIQUES ─────────────────────────────────────────────────────────
    ("Amoxicilline EG 500mg",      "Amoxicilline",       "antibiotic", "Gélule",       ["250mg","500mg"],140.00,True,  True,  "EG Pharma"),
    ("Amoxicilline EG 1g",         "Amoxicilline",       "antibiotic", "Comprimé dispersible",["1g"],   185.00, True,  True,  "EG Pharma"),
    ("Augmentin 1g",               "Amoxicilline + Acide clavulanique","antibiotic","Comprimé",["1g"],  320.00, True,  True,  "GlaxoSmithKline"),
    ("Ciprofloxacine Teva 500mg",  "Ciprofloxacine",     "antibiotic", "Comprimé",     ["500mg"],       280.00, True,  True,  "Teva"),
    ("Azithromycine Mylan 500mg",  "Azithromycine",      "antibiotic", "Comprimé",     ["250mg","500mg"],310.00,True,  True,  "Mylan"),
    ("Céfixime EG 200mg",          "Céfixime",           "antibiotic", "Comprimé",     ["200mg"],       350.00, True,  True,  "EG Pharma"),

    # ── ANALGÉSIQUES / ANTIPYRÉTIQUES ─────────────────────────────────────────
    ("Paracétamol Générique 500mg","Paracétamol",        "analgesic",  "Comprimé",     ["500mg"],        55.00, True,  False, "Générique"),
    ("Paracétamol Générique 1g",   "Paracétamol",        "analgesic",  "Comprimé",     ["1g"],           75.00, True,  False, "Générique"),
    ("Dafalgan 1g",                "Paracétamol",        "analgesic",  "Comprimé effervescent",["1g"],  110.00, True,  False, "UPSA"),
    ("Doliprane 1g",               "Paracétamol",        "analgesic",  "Comprimé",     ["500mg","1g"],  105.00, True,  False, "Sanofi"),
    ("Tramadol Mylan 50mg",        "Tramadol HCl",       "analgesic",  "Gélule",       ["50mg","100mg"],240.00, True,  True,  "Mylan"),
    ("Codeine Phosphate 30mg",     "Codéine phosphate",  "analgesic",  "Comprimé",     ["30mg"],        195.00, True,  True,  "Bristol"),

    # ── ANTI-INFLAMMATOIRES ───────────────────────────────────────────────────
    ("Ibuprofène EG 400mg",        "Ibuprofène",         "anti_inflam","Comprimé",     ["200mg","400mg"], 95.00,True,  False, "EG Pharma"),
    ("Diclofénac Sandoz 75mg",     "Diclofénac sodique", "anti_inflam","Comprimé",     ["50mg","75mg"], 165.00, True,  True,  "Sandoz"),
    ("Voltarène Gel 1%",           "Diclofénac diéthylamine","anti_inflam","Gel",      ["1%"],          280.00, False, False, "Novartis"),
    ("Kétoprofène Mylan 100mg",    "Kétoprofène",        "anti_inflam","Comprimé",     ["100mg"],       180.00, True,  True,  "Mylan"),
    ("Myolastan 50mg",             "Tétrazépam",         "anti_inflam","Comprimé",     ["50mg"],        220.00, True,  True,  "Sanofi"),
    ("Cortancyl 5mg",              "Prednisone",         "anti_inflam","Comprimé",     ["5mg","20mg"],  145.00, True,  True,  "Sanofi"),
    ("Prednisolone EG 20mg",       "Prednisolone",       "anti_inflam","Comprimé",     ["5mg","20mg"],  160.00, True,  True,  "EG Pharma"),

    # ── GASTRO-ENTÉROLOGIE ────────────────────────────────────────────────────
    ("Oméprazole EG 20mg",         "Oméprazole",         "gastro",     "Gélule",       ["10mg","20mg"], 145.00, True,  False, "EG Pharma"),
    ("Pantoprazole Mylan 40mg",    "Pantoprazole",       "gastro",     "Comprimé",     ["20mg","40mg"], 195.00, True,  True,  "Mylan"),
    ("Spasfon 80mg",               "Phloroglucinol",     "gastro",     "Comprimé",     ["80mg"],         85.00, True,  False, "Teva"),
    ("Smecta 3g sachet",           "Diosmectite",        "gastro",     "Poudre orale", ["3g"],           65.00, True,  False, "Ipsen"),
    ("Motilium 10mg",              "Dompéridone",        "gastro",     "Comprimé",     ["10mg"],        120.00, True,  False, "Janssen"),
    ("Imodium 2mg",                "Lopéramide HCl",     "gastro",     "Gélule",       ["2mg"],         110.00, False, False, "Janssen"),
    ("Gaviscon suspension",        "Alginate de sodium", "gastro",     "Suspension orale",["500mg/10mL"],190.00,False,False, "Reckitt"),

    # ── NEUROLOGIE / PSYCHIATRIE ──────────────────────────────────────────────
    ("Mélatonine Circadin 2mg",    "Mélatonine",         "neuro",      "Comprimé LP",  ["2mg"],         380.00, False, False, "Rad Pharma"),
    ("Lexomil 6mg",                "Bromazépam",         "neuro",      "Comprimé",     ["6mg"],         165.00, True,  True,  "Roche"),
    ("Stilnox 10mg",               "Zolpidem tartrate",  "neuro",      "Comprimé",     ["10mg"],        210.00, True,  True,  "Sanofi"),

    # ── AUTRES / VITAMINES ────────────────────────────────────────────────────
    ("Rhinofluimucil spray",       "Acétylcystéine + Tuaminoheptane","other","Spray nasal",["0.9%"],    195.00, False, False, "Zambon"),
    ("Loratadine EG 10mg",         "Loratadine",         "other",      "Comprimé",     ["10mg"],         95.00, True,  False, "EG Pharma"),
    ("Cétirizine Mylan 10mg",      "Cétirizine HCl",     "other",      "Comprimé",     ["10mg"],        105.00, True,  False, "Mylan"),
    ("Vitamine C 500mg",           "Acide ascorbique",   "other",      "Comprimé effervescent",["500mg"],75.00, False, False, "UPSA"),
    ("Vitamine D3 800UI",          "Cholécalciférol",    "other",      "Comprimé",     ["800UI"],       145.00, True,  False, "Sandoz"),
    ("Acide folique 5mg",          "Acide folique",      "other",      "Comprimé",     ["5mg"],          60.00, True,  False, "EG Pharma"),
    ("Vitamine B6 40mg",           "Pyridoxine HCl",     "other",      "Comprimé",     ["40mg"],         80.00, True,  False, "Générique"),
    ("Magnésium B6",               "Magnésium lactate + Vitamine B6","other","Comprimé",["48mg+5mg"],   175.00, False, False, "Sanofi"),
    ("Magnésium Marin 300mg",      "Magnésium",          "other",      "Comprimé",     ["300mg"],       220.00, False, False, "Santé Verte"),
    ("Zinc Oligosol",              "Gluconate de zinc",  "other",      "Ampoule buvable",["0.1mg/2mL"], 190.00, False, False, "Labcatal"),
    ("Fer Tardyferon 80mg",        "Fumarate ferreux",   "other",      "Comprimé",     ["80mg"],        145.00, True,  False, "Pierre Fabre"),
    ("Calcium Sandoz 500mg",       "Carbonate de calcium","other",     "Comprimé effervescent",["500mg"],110.00,False, False, "Sandoz"),
    ("Actonel 35mg",               "Risédronate sodium", "other",      "Comprimé",     ["35mg"],        680.00, True,  True,  "Procter & Gamble"),
    ("Seretide Diskus 50/250",     "Salmétérol + Fluticasone","other","Poudre inhalation",["50/250mcg"],1150.00,True, True,  "GSK"),
    ("Ventoline 100mcg",           "Salbutamol",         "other",      "Aérosol",      ["100mcg/dose"], 320.00, True,  True,  "GSK"),
]

# ─── Stock par médicament ─────────────────────────────────────────────────────
# (barcode_suffix, quantity, prix_vente, expiry)
STOCK_CONFIG = {
    "Amlodipine Biogaran 5mg":     ("BC-001", 85,  210,  date(2027, 6, 30)),
    "Amlodipine Biogaran 10mg":    ("BC-002", 60,  275,  date(2027, 6, 30)),
    "Lisinopril EG 10mg":          ("BC-003", 72,  225,  date(2027, 3, 31)),
    "Losartan Teva 50mg":          ("BC-004", 55,  255,  date(2027, 4, 30)),
    "Ramipril Sandoz 5mg":         ("BC-005", 48,  240,  date(2027, 5, 31)),
    "Aténolol Pharmos 50mg":       ("BC-006", 40,  215,  date(2026, 12, 31)),
    "Furosémide Générique 40mg":   ("BC-007", 90,  140,  date(2027, 8, 31)),
    "Spironolactone EG 25mg":      ("BC-008", 35,  350,  date(2027, 2, 28)),
    "Trinitrine Spray":            ("BC-009", 18,  520,  date(2026, 9, 30)),
    "Aspirine Cardio 100mg":       ("BC-010", 120, 110,  date(2027, 12, 31)),
    "Atorvastatine Mylan 20mg":    ("BC-011", 65,  320,  date(2027, 7, 31)),
    "Oméga-3 Pharmos 1g":          ("BC-012", 30,  450,  date(2026, 11, 30)),
    "Valsartan Teva 80mg":         ("BC-013", 42,  295,  date(2027, 5, 31)),
    "Metformine EG 500mg":         ("BC-014", 110, 130,  date(2027, 10, 31)),
    "Metformine EG 1000mg":        ("BC-015", 95,  200,  date(2027, 10, 31)),
    "Glucophage 500mg":            ("BC-016", 80,  205,  date(2027, 9, 30)),
    "Glucophage XR 1000mg":        ("BC-017", 55,  255,  date(2027, 8, 31)),
    "Glimépéride Sandoz 2mg":      ("BC-018", 45,  225,  date(2027, 6, 30)),
    "Insuline Actrapid FlexPen":   ("BC-019", 20,  1050, date(2026, 8, 31)),
    "Insuline Lantus SoloStar":    ("BC-020", 15,  1450, date(2026, 7, 31)),
    "Bandelettes Glycémiques x50": ("BC-021", 25,  750,  date(2027, 3, 31)),
    "Amoxicilline EG 500mg":       ("BC-022", 75,  160,  date(2027, 1, 31)),
    "Amoxicilline EG 1g":          ("BC-023", 60,  210,  date(2027, 1, 31)),
    "Augmentin 1g":                ("BC-024", 40,  370,  date(2026, 10, 31)),
    "Ciprofloxacine Teva 500mg":   ("BC-025", 30,  320,  date(2027, 2, 28)),
    "Azithromycine Mylan 500mg":   ("BC-026", 28,  360,  date(2026, 12, 31)),
    "Céfixime EG 200mg":           ("BC-027", 35,  400,  date(2027, 3, 31)),
    "Paracétamol Générique 500mg": ("BC-028", 200, 65,   date(2028, 1, 31)),
    "Paracétamol Générique 1g":    ("BC-029", 180, 88,   date(2028, 1, 31)),
    "Dafalgan 1g":                 ("BC-030", 90,  125,  date(2027, 11, 30)),
    "Doliprane 1g":                ("BC-031", 95,  120,  date(2027, 11, 30)),
    "Tramadol Mylan 50mg":         ("BC-032", 22,  275,  date(2027, 6, 30)),
    "Codeine Phosphate 30mg":      ("BC-033", 15,  225,  date(2027, 4, 30)),
    "Ibuprofène EG 400mg":         ("BC-034", 130, 110,  date(2028, 2, 28)),
    "Diclofénac Sandoz 75mg":      ("BC-035", 65,  190,  date(2027, 8, 31)),
    "Voltarène Gel 1%":            ("BC-036", 40,  320,  date(2027, 7, 31)),
    "Kétoprofène Mylan 100mg":     ("BC-037", 50,  205,  date(2027, 5, 31)),
    "Myolastan 50mg":              ("BC-038", 35,  255,  date(2027, 3, 31)),
    "Cortancyl 5mg":               ("BC-039", 45,  170,  date(2027, 9, 30)),
    "Prednisolone EG 20mg":        ("BC-040", 40,  185,  date(2027, 9, 30)),
    "Oméprazole EG 20mg":          ("BC-041", 150, 165,  date(2027, 12, 31)),
    "Pantoprazole Mylan 40mg":     ("BC-042", 80,  225,  date(2027, 10, 31)),
    "Spasfon 80mg":                ("BC-043", 110, 98,   date(2028, 3, 31)),
    "Smecta 3g sachet":            ("BC-044", 120, 75,   date(2028, 3, 31)),
    "Motilium 10mg":               ("BC-045", 75,  140,  date(2027, 8, 31)),
    "Imodium 2mg":                 ("BC-046", 60,  125,  date(2028, 1, 31)),
    "Gaviscon suspension":         ("BC-047", 45,  220,  date(2027, 6, 30)),
    "Mélatonine Circadin 2mg":     ("BC-048", 25,  440,  date(2027, 5, 31)),
    "Lexomil 6mg":                 ("BC-049", 20,  190,  date(2027, 4, 30)),
    "Stilnox 10mg":                ("BC-050", 18,  240,  date(2027, 3, 31)),
    "Rhinofluimucil spray":        ("BC-051", 55,  225,  date(2027, 2, 28)),
    "Loratadine EG 10mg":          ("BC-052", 100, 110,  date(2028, 4, 30)),
    "Cétirizine Mylan 10mg":       ("BC-053", 95,  120,  date(2028, 4, 30)),
    "Vitamine C 500mg":            ("BC-054", 110, 88,   date(2028, 6, 30)),
    "Vitamine D3 800UI":           ("BC-055", 70,  168,  date(2027, 12, 31)),
    "Acide folique 5mg":           ("BC-056", 85,  72,   date(2028, 5, 31)),
    "Vitamine B6 40mg":            ("BC-057", 90,  95,   date(2028, 5, 31)),
    "Magnésium B6":                ("BC-058", 65,  200,  date(2027, 10, 31)),
    "Magnésium Marin 300mg":       ("BC-059", 50,  255,  date(2027, 9, 30)),
    "Zinc Oligosol":               ("BC-060", 40,  220,  date(2027, 8, 31)),
    "Fer Tardyferon 80mg":         ("BC-061", 60,  168,  date(2027, 11, 30)),
    "Calcium Sandoz 500mg":        ("BC-062", 75,  128,  date(2028, 2, 28)),
    "Actonel 35mg":                ("BC-063", 12,  780,  date(2027, 1, 31)),
    "Seretide Diskus 50/250":      ("BC-064", 10, 1320,  date(2026, 10, 31)),
    "Ventoline 100mcg":            ("BC-065", 30,  370,  date(2027, 7, 31)),
}

# ─── Création des médicaments et du stock ─────────────────────────────────────
print(f"\nCréation du catalogue ({len(CATALOG)} médicaments) et du stock...")
created_meds = 0
created_stock = 0
skipped = 0

for (name, molecule, category, form, dosage_forms, price, cnas, req_presc, manufacturer) in CATALOG:
    # Créer ou récupérer le médicament
    barcode_suffix = STOCK_CONFIG.get(name, (f"BC-ELSHIFA-{name[:10]}", 0, 0, None))[0]
    barcode = f"ELSHIFA-{barcode_suffix}"

    med, med_created = Medication.objects.get_or_create(
        name=name,
        defaults={
            'molecule':     molecule,
            'category':     category,
            'form':         form,
            'dosage_forms': dosage_forms,
            'price_dzd':    price,
            'cnas_covered': cnas,
            'requires_prescription': req_presc,
            'manufacturer': manufacturer,
            'is_active':    True,
            'barcode':      barcode,
        }
    )
    if med_created:
        created_meds += 1

    # Créer ou mettre à jour le stock
    if name in STOCK_CONFIG:
        _, qty, selling_price, expiry = STOCK_CONFIG[name]
        stock, stock_created = PharmacyStock.objects.get_or_create(
            pharmacy=pharmacy,
            medication=med,
            defaults={
                'quantity':      qty,
                'selling_price': selling_price,
                'expiry_date':   expiry,
            }
        )
        if stock_created:
            created_stock += 1
            cat_emoji = {'cardio':'❤️','diabetes':'🩸','antibiotic':'💊','analgesic':'🔵',
                         'anti_inflam':'🟡','gastro':'🟢','neuro':'🟣','other':'⚪'}.get(category,'•')
            print(f"  {cat_emoji} {name:<42} {qty:>4} unités  {selling_price:>7.0f} DZD")
        else:
            skipped += 1


# ─── Rapport ──────────────────────────────────────────────────────────────────
total_stock = PharmacyStock.objects.filter(pharmacy=pharmacy).count()
total_units = sum(s.quantity for s in PharmacyStock.objects.filter(pharmacy=pharmacy))
valeur = sum(s.quantity * s.selling_price for s in PharmacyStock.objects.filter(pharmacy=pharmacy))

print(f"\n{'=' * 60}")
print("RAPPORT STOCK — Pharmacie El Shifa")
print("=" * 60)
print(f"✅ Médicaments créés dans le catalogue : {created_meds}")
print(f"✅ Références en stock créées          : {created_stock}")
print(f"⏭️  Déjà existantes (ignorées)         : {skipped}")
print()
print(f"📦 Total références en stock    : {total_stock}")
print(f"🔢 Total unités en stock        : {total_units}")
print(f"💰 Valeur totale du stock       : {valeur:,.0f} DZD")
print()

# Répartition par catégorie
from django.db.models import Sum, Count
cats = {'cardio':'Cardiologie','diabetes':'Diabétologie','antibiotic':'Antibiotiques',
        'analgesic':'Analgésiques','anti_inflam':'Anti-inflammatoires',
        'gastro':'Gastro-entérologie','neuro':'Neurologie','other':'Autres'}
for cat_key, cat_label in cats.items():
    stocks = PharmacyStock.objects.filter(pharmacy=pharmacy, medication__category=cat_key)
    n = stocks.count()
    if n:
        units = sum(s.quantity for s in stocks)
        print(f"  {cat_label:<25} {n:>3} références  {units:>5} unités")

print("=" * 60)
print("Stock rempli avec succès.")
