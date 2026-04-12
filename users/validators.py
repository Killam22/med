import magic
from django.core.exceptions import ValidationError

# Liste stricte des types de fichiers que tu autorises
ALLOWED_MIMES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
}

def validate_file_type(file):
    """
    Vérifie la vraie nature du fichier en lisant ses premiers octets.
    """
    # 1. On lit les 2048 premiers octets (largement suffisant pour trouver la signature)
    file_content = file.read(2048)
    
    # 2. On demande à 'magic' de deviner le vrai type MIME
    mime_type = magic.from_buffer(file_content, mime=True)
    
    # 3. TRÈS IMPORTANT : On remet le curseur de lecture au début du fichier !
    # Si on oublie ça, Django enregistrera le fichier en amputant les 2048 premiers octets.
    file.seek(0)
    
    # 4. On vérifie si c'est autorisé
    if mime_type not in ALLOWED_MIMES:
        raise ValidationError(
            f"Fichier invalide ou corrompu. Attendu: PDF/JPG/PNG. Détecté: {mime_type}"
        )