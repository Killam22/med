from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import AuditLog

User = get_user_model()

class AdminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    submitted_documents = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'email', 'role', 'is_active', 
            'verification_status', 'date_joined', 'submitted_documents'
        ]

    def get_submitted_documents(self, obj):
        """Récupère dynamiquement les documents selon l'architecture exacte de la BDD"""
        docs = []
        request = self.context.get('request')
        
        # Fonction utilitaire pour générer l'URL absolue du fichier (ex: http://127.0.0.1:8000/media/...)
        def build_url(file_field):
            if file_field and hasattr(file_field, 'url'):
                return request.build_absolute_uri(file_field.url) if request else file_field.url
            return None

        try:
            if obj.role == 'doctor':
                # On utilise 'doctor_profile' comme défini dans ton modèle Doctor
                profile = getattr(obj, 'doctor_profile', None) 
                if profile:
                    # L'autorisation d'exercer
                    if getattr(profile, 'practice_authorization', None):
                        docs.append({
                            "title": "Autorisation d'exercer", 
                            "url": build_url(profile.practice_authorization)
                        })
                    
                    # Les diplômes liés via 'qualifications' (DoctorQualification)
                    for qual in profile.qualifications.all():
                        if getattr(qual, 'scan', None):
                            docs.append({
                                "title": f"Diplôme: {qual.title} ({qual.degree_type})", 
                                "url": build_url(qual.scan)
                            })

            elif obj.role == 'pharmacist':
                # On utilise 'pharmacist_profile'
                profile = getattr(obj, 'pharmacist_profile', None)
                if profile:
                    # La licence d'exploitation
                    if getattr(profile, 'pharmacy_license', None):
                        docs.append({
                            "title": "Licence d'exploitation", 
                            "url": build_url(profile.pharmacy_license)
                        })
                    
                    # Les diplômes (PharmacistQualification)
                    for qual in profile.qualifications.all():
                        if getattr(qual, 'scan', None):
                            docs.append({
                                "title": f"Diplôme: {qual.title}", 
                                "url": build_url(qual.scan)
                            })

            elif obj.role == 'caretaker':
                # On utilise 'caretaker_profile'
                profile = getattr(obj, 'caretaker_profile', None)
                if profile:
                    # Les certificats (CaretakerCertificate)
                    for cert in profile.certificates.all():
                        if getattr(cert, 'scan', None):
                            docs.append({
                                "title": f"Certificat: {cert.name}", 
                                "url": build_url(cert.scan)
                            })
                        
        except Exception as e:
            # Sécurité pour éviter un crash d'API si un profil est mal configuré
            print(f"Avertissement lors de la récupération des docs pour {obj.email}: {str(e)}")
            
        return docs

class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True, default='Système')
    
    class Meta:
        model = AuditLog
        fields = ['id', 'level', 'message', 'actor_name', 'ip_address', 'created_at']