import pandas as pd
from django.core.management.base import BaseCommand
from medications.models import Medication

class Command(BaseCommand):
    help = 'Charge la nomenclature depuis le fichier Excel officiel du Ministère avec nettoyage des catégories'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Chemin vers le fichier .xlsx')

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        
        # --- 1. RÈGLES DE CATÉGORISATION (Data Cleaning) ---
        # Valeurs correspondant exactement aux choices du modèle Medication.Category
        categories_rules = {
            'PARACETAMOL': 'analgesic',
            'AMOXICILLINE': 'antibiotic',
            'CEF': 'antibiotic',       # Cefotaxime, Ceftriaxone, Cefixime...
            'PENICILLINE': 'antibiotic',
            'IBUPROFENE': 'anti_inflam',
            'DICLOFENAC': 'anti_inflam',
            'KETOPROFENE': 'anti_inflam',
            'CORTISONE': 'anti_inflam',
            'PREDNISOLONE': 'anti_inflam',
            'METFORMINE': 'diabetes',
            'INSULINE': 'diabetes',
            'GLIMEPIRIDE': 'diabetes',
            'OMEPRAZOLE': 'gastro',
            'PANTOPRAZOLE': 'gastro',
            'AMLODIPINE': 'cardio',
            'VALSARTAN': 'cardio',
            'LOSARTAN': 'cardio',
            'LORATADINE': 'other',
            'CETIRIZINE': 'other',
            'VITAMINE': 'other',
            'CALCIUM': 'other',
            'FER': 'other',
        }

        # Fonction qui trouve la catégorie en lisant la molécule
        def trouver_categorie(dci):
            if not dci or str(dci).lower() == 'nan':
                return 'other'
            dci_upper = str(dci).upper()
            for mot_cle, cat in categories_rules.items():
                if mot_cle in dci_upper:
                    return cat
            return 'other'
        # ----------------------------------------------------

        try:
            self.stdout.write("Ouverture du fichier Excel en cours (cela peut prendre 1 à 2 minutes)...")
            xls = pd.ExcelFile(excel_file, engine='openpyxl')
            total_added = 0
            
            for sheet_name in xls.sheet_names:
                is_active = not ('retrait' in sheet_name.lower() or 'renouvel' in sheet_name.lower())
                statut = "ACTIF" if is_active else "INACTIF"
                self.stdout.write(f"\nTraitement de l'onglet : '{sheet_name}' (Statut : {statut})")
                
                df = pd.read_excel(xls, sheet_name=sheet_name, skiprows=13)
                df = df.fillna('')
                
                count = 0
                for index, row in df.iterrows():
                    nom_marque = str(row.get('NOM DE MARQUE', '')).strip()
                    if not nom_marque or nom_marque.lower() == 'nan':
                        continue
                        
                    # --- COUPURE DE SÉCURITÉ ICI POUR ÉVITER LES CRASHS DB ---
                    molecule = str(row.get('DENOMINATION COMMUNE INTERNATIONALE', '')).strip()[:240]
                    forme = str(row.get('FORME', '')).strip()[:240]
                    dosage = str(row.get('DOSAGE', '')).strip()[:100]
                    labo = str(row.get("LABORATOIRES DETENTEUR DE LA DECISION D'ENREGISTREMENT", '')).strip()[:240]
                    liste = str(row.get('LISTE', '')).strip()
                    num_enreg = str(row.get('N°ENREGISTREMENT', '')).strip()[:90]
                    # ---------------------------------------------------------

                    if not num_enreg:
                        continue
                    
                    base_name = f"{nom_marque} - {dosage}" if dosage else nom_marque
                    full_name = base_name[:150] # On coupe à 150 pour garder de la place pour le code-barres
                    
                    existing_med = Medication.objects.filter(name=full_name).first()
                    if existing_med and existing_med.barcode != num_enreg:
                        full_name = f"{full_name} [{num_enreg}]"

                    # 2. APPLICATION DU NETTOYAGE
                    requires_presc = 'liste' in liste.lower() or 'stup' in liste.lower()
                    categorie_calculee = trouver_categorie(molecule) # Calcul dynamique de la catégorie
                    
                    dosage_json = [dosage] if dosage else []

                    # Insertion ou mise à jour
                    med, created = Medication.objects.update_or_create(
                        barcode=num_enreg,
                        defaults={
                            'name': full_name[:240], # Sécurité finale à 240
                            'molecule': molecule,
                            'form': forme,
                            'category': categorie_calculee, # <--- Ajout de la catégorie ici
                            'dosage_forms': dosage_json,
                            'manufacturer': labo,
                            'requires_prescription': requires_presc,
                            'is_active': is_active,
                        }
                    )
                    count += 1
                    if created:
                        total_added += 1

                self.stdout.write(self.style.SUCCESS(f' -> {count} médicaments traités depuis cet onglet ({total_added} créés au total).'))
                
            self.stdout.write(self.style.SUCCESS(f'\nTerminé avec succès ! {total_added} médicaments importés au total.'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Une erreur est survenue : {str(e)}'))