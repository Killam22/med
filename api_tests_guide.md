# Guide de Tests API (Django REST Framework)

Voici la liste des tests à effectuer via l'interface navigable de DRF (ou Postman/Insomnia) pour s'assurer que ton nouveau module Pharmacie et la séparation des médicaments fonctionnent parfaitement.

Tous les endpoints nécessitent au minium un **Token JWT** (`Authorization: Bearer <token>`) sauf mention contraire. Assure-toi d'avoir un utilisateur Pharmacien, un Patient, un Médecin et un Administrateur sous la main.

---

## 1. Registre Global des Médicaments (`medications`)

**L'objectif :** Vérifier que la base nationale est bien en lecture seule pour le public et modifiable uniquement par l'admin.

| Acteur | Méthode | Endpoint | Body (JSON) attendu / Action | Résultat attendu |
| :--- | :---: | :--- | :--- | :--- |
| **Patient** | `GET` | `/api/medications/registry/` | _Aucun_ | Liste des médicaments (statut 200).
| **Patient** | `POST` | `/api/medications/registry/` | `{"name": "Doliprane", ...}` | **Erreur 403** (Forbidden).
| **Admin** | `POST` | `/api/medications/registry/` | `{"name": "Doliprane", "molecule": "Paracétamol", "price_dzd": "250.00", "is_shifa_compatible": true}` | Création réussie (statut 201).
| **Médecin** | `GET` | `/api/medications/registry/?search=Doliprane` | _Aucun_ | Recherche via SearchFilter, retourne le Doliprane créé.

---

## 2. Inventaire Local du Pharmacien (`pharmacy/stock`)

**L'objectif :** Sécuriser l'inventaire. Un pharmacien ne doit gérer et voir **que** son propre stock.

| Acteur | Méthode | Endpoint | Body (JSON) attendu / Action | Résultat attendu |
| :--- | :---: | :--- | :--- | :--- |
| **Pharmacien** | `GET` | `/api/pharmacy/stock/` | _Aucun_ | Doit retourner `[]` (vide, statut 200).
| **Pharmacien** | `POST` | `/api/pharmacy/stock/` | `{"pharmacist": "<id_pharmacist>", "medication": "<id_doliprane>", "quantity": 50, "selling_price": "260.00"}` | Création du stock (statut 201). **Note**: Assure-toi d'utiliser l'ID de ton profil `Pharmacist`!
| **Pharmacien** | `POST` | `/api/pharmacy/stock/` | `{"pharmacist": "<id_pharmacist>", "medication": "<id_doliprane>", "quantity": -5, "selling_price": "260.00" }` | **Erreur 400** (Validation : Quantité ne peut pas être négative).
| **Pharmacien 2** | `GET` | `/api/pharmacy/stock/` | _Aucun_ | Ne voit **pas** le stock du Pharmacien 1 (statut 200, liste vide).

---

## 3. Géolocalisation & Recherche Stock (`search-nearby`)

**L'objectif :** Côté patient, trouver une pharmacie qui a le médicament en stock.

| Acteur | Méthode | Endpoint | Action | Résultat attendu |
| :--- | :---: | :--- | :--- | :--- |
| **Patient** | `GET` | `/api/pharmacy/stock/search-nearby/?medication_id=<id>&lat=36.75&lon=3.04` | Recherche le médicament. | Retourne la liste des pharmacies (Nom, Distance calculée, prix et stock). Si le stock de la pharmacie est à 0, elle ne doit pas apparaître.

---

## 4. Worklow de Commandes (`pharmacy/orders`)

**L'objectif :** Envoyer une ordonnance à la pharmacie et gérer le cycle de vie de la commande.

### Étape 4.1 : Création (Patient)
| Acteur | Méthode | Endpoint | Body (JSON) attendu / Action | Résultat attendu |
| :--- | :---: | :--- | :--- | :--- |
| **Patient** | `POST` | `/api/pharmacy/orders/` | `{"prescription": "<id_ordonnance>", "patient_message": "Merci de préparer vite"}` | Commande créée (statut 201).
| **Patient** | `GET` | `/api/pharmacy/orders/` | _Aucun_ | Voit sa commande avec le statut "pending".

### Étape 4.2 : Traitement (Pharmacien)
| Acteur | Méthode | Endpoint | Body (JSON) attendu / Action | Résultat attendu |
| :--- | :---: | :--- | :--- | :--- |
| **Pharmacien** | `GET` | `/api/pharmacy/orders/incoming/` | _Aucun_ | Voit la commande du patient en attente.
| **Pharmacien** | `PATCH` | `/api/pharmacy/orders/<id_commande>/status/` | `{"status": "preparing", "pharmacist_note": "Commande en cours"}` | Statut mis à jour (200 OK). Le champ `pharmacist` est assigné automatiquement à ce pharmacien.

---

## 5. Intégrité des Ordonnances (`prescriptions`)

**L'objectif :** S'assurer que le médecin peut insérer des médicaments issus de la nouvelle base de données dans son ordonnance.

| Acteur | Méthode | Endpoint | Body (JSON) attendu / Action | Résultat attendu |
| :--- | :---: | :--- | :--- | :--- |
| **Médecin** | `POST` | `/api/prescriptions/` | `{"consultation": "<id>", "valid_until": "2026-12-31", "items": [{"medication": "<id_medicament_global>", "drug_name": "Doliprane", "frequency": "1x_day", "quantity": 2, "dosage": "500", "duration": "5"}]}` | L'ordonnance est créée, et `items` renvoie bien l'ID du médicament associé à la base nationale.

> [!TIP]
> Si tout passe dans DRF Browsable API (ou Postman), cela signifie que tes modèles, tes ForeignKeys et tes permission de vue sont béton ! Tu pourras envoyer les requêtes sereinement au développeur React.
