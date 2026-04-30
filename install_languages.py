# Créez ce fichier : dataset/install_languages.py
import argostranslate.package
import argostranslate.translate

print("Téléchargement des langues...")

argostranslate.package.update_package_index()
available = argostranslate.package.get_available_packages()

# Anglais → Français
pkg_fr = next(p for p in available if p.from_code == "en" and p.to_code == "fr")
argostranslate.package.install_from_path(pkg_fr.download())
print("✅ EN → FR installé")

# Anglais → Arabe
pkg_ar = next(p for p in available if p.from_code == "en" and p.to_code == "ar")
argostranslate.package.install_from_path(pkg_ar.download())
print("✅ EN → AR installé")

print("✅ Langues installées avec succès !")