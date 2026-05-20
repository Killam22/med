from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import AuditLog

User = get_user_model()

class AdminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    submitted_documents = serializers.SerializerMethodField()
    patient_detail = serializers.SerializerMethodField()
    specialty = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'first_name', 'last_name', 'email', 'role',
            'is_active', 'verification_status', 'date_joined',
            'submitted_documents', 'phone', 'wilaya',
            'address', 'city', 'postal_code', 'sex', 'date_of_birth', 'id_card_number',
            'patient_detail', 'specialty',
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
            if obj.role == 'patient':
                if getattr(obj, 'id_card_recto', None):
                    docs.append({"title": "CIN Recto", "url": build_url(obj.id_card_recto)})
                if getattr(obj, 'id_card_verso', None):
                    docs.append({"title": "CIN Verso", "url": build_url(obj.id_card_verso)})
                if getattr(obj, 'photo', None):
                    docs.append({"title": "Photo de profil", "url": build_url(obj.photo)})

            elif obj.role == 'doctor':
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

    def get_patient_detail(self, obj):
        """Retourne le profil médical si l'utilisateur est un patient."""
        if obj.role != 'patient':
            return None
        try:
            mp = obj.patient_profile.medical_profile
            return {
                'medical_profile': {
                    'blood_group': mp.blood_group or '',
                    'height': mp.height,
                    'weight': mp.weight,
                }
            }
        except Exception:
            return {'medical_profile': {'blood_group': '', 'height': None, 'weight': None}}

    def get_specialty(self, obj):
        if obj.role == 'doctor':
            try:
                return obj.doctor_profile.specialty or ''
            except Exception:
                pass
        return ''

    def update(self, instance, validated_data):
        # Champs médicaux transmis hors validated_data (non déclarés dans Meta.fields)
        request_data = self.context.get('request').data if self.context.get('request') else {}
        blood_group = request_data.get('blood_group') or request_data.get('blood_type')
        height = request_data.get('height')
        weight = request_data.get('weight')

        instance = super().update(instance, validated_data)

        if instance.role == 'patient' and any([blood_group, height, weight]):
            try:
                patient = instance.patient_profile
                mp, _ = patient.medical_profile.__class__.objects.get_or_create(patient=patient)
                if blood_group is not None:
                    mp.blood_group = blood_group
                if height is not None:
                    try:
                        mp.height = float(height)
                    except (ValueError, TypeError):
                        pass
                if weight is not None:
                    try:
                        mp.weight = float(weight)
                    except (ValueError, TypeError):
                        pass
                mp.save()
            except Exception:
                pass

        return instance


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True, default='Système')
    
    class Meta:
        model = AuditLog
        fields = ['id', 'level', 'message', 'actor_name', 'ip_address', 'created_at']