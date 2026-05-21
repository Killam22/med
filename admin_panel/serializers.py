from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import AuditLog

User = get_user_model()


def _build_url(request, file_field):
    if file_field and hasattr(file_field, 'url'):
        try:
            return request.build_absolute_uri(file_field.url) if request else file_field.url
        except Exception:
            return None
    return None


class AdminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    submitted_documents = serializers.SerializerMethodField()
    patient_detail = serializers.SerializerMethodField()
    doctor_detail = serializers.SerializerMethodField()
    pharmacist_detail = serializers.SerializerMethodField()
    caretaker_detail = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'first_name', 'last_name', 'email', 'role',
            'is_active', 'verification_status', 'date_joined',
            'phone', 'wilaya', 'address', 'city', 'postal_code',
            'sex', 'date_of_birth', 'id_card_number', 'photo',
            'submitted_documents',
            'patient_detail', 'doctor_detail', 'pharmacist_detail', 'caretaker_detail',
        ]

    def get_submitted_documents(self, obj):
        docs = []
        request = self.context.get('request')

        # Documents identité communs à tous les rôles
        if getattr(obj, 'id_card_recto', None):
            docs.append({"title": "CIN Recto", "url": _build_url(request, obj.id_card_recto)})
        if getattr(obj, 'id_card_verso', None):
            docs.append({"title": "CIN Verso", "url": _build_url(request, obj.id_card_verso)})
        if getattr(obj, 'photo', None):
            docs.append({"title": "Photo de profil", "url": _build_url(request, obj.photo)})

        try:
            if obj.role == 'doctor':
                profile = getattr(obj, 'doctor_profile', None)
                if profile:
                    if getattr(profile, 'practice_authorization', None):
                        docs.append({
                            "title": "Autorisation d'exercer",
                            "url": _build_url(request, profile.practice_authorization),
                        })
                    for dip in profile.diplomas.all():
                        docs.append({
                            "title": f"Diplôme — {dip.title}",
                            "subtitle": f"{dip.institution} · {dip.date_obtained}",
                            "url": _build_url(request, dip.file) if getattr(dip, 'file', None) else None,
                        })

            elif obj.role == 'pharmacist':
                profile = getattr(obj, 'pharmacist_profile', None)
                if profile:
                    pharmacy = getattr(profile, 'pharmacy', None)
                    if pharmacy:
                        if getattr(pharmacy, 'agreement_scan', None):
                            docs.append({
                                "title": "Agrément pharmacie",
                                "url": _build_url(request, pharmacy.agreement_scan),
                            })
                        if getattr(pharmacy, 'registre_commerce', None):
                            docs.append({
                                "title": "Registre de commerce",
                                "url": _build_url(request, pharmacy.registre_commerce),
                            })

            elif obj.role == 'caretaker':
                profile = getattr(obj, 'caretaker_profile', None)
                if profile:
                    if getattr(profile, 'criminal_record_scan', None):
                        docs.append({
                            "title": "Extrait de casier judiciaire",
                            "url": _build_url(request, profile.criminal_record_scan),
                        })
                    for dip in profile.diplomas.all():
                        docs.append({
                            "title": f"Diplôme — {dip.title}",
                            "subtitle": f"{dip.institution} · {dip.date_obtained}",
                            "url": _build_url(request, dip.file) if getattr(dip, 'file', None) else None,
                        })

        except Exception as e:
            print(f"[AdminUserSerializer] docs error for {obj.email}: {e}")

        return docs

    def get_patient_detail(self, obj):
        if obj.role != 'patient':
            return None
        try:
            mp = obj.patient_profile.medical_profile
            return {'blood_group': mp.blood_group or '', 'height': mp.height, 'weight': mp.weight}
        except Exception:
            return {'blood_group': '', 'height': None, 'weight': None}

    def get_doctor_detail(self, obj):
        if obj.role != 'doctor':
            return None
        try:
            p = obj.doctor_profile
            return {
                'specialty': p.get_specialty_display(),
                'order_number': p.order_number,
                'clinic_name': p.clinic_name,
                'experience_years': p.experience_years,
                'consultation_fee': str(p.consultation_fee),
                'cnas_coverage': p.cnas_coverage,
                'bio': p.bio,
                'rating': str(p.rating),
                'is_verified': p.is_verified,
            }
        except Exception:
            return None

    def get_pharmacist_detail(self, obj):
        if obj.role != 'pharmacist':
            return None
        try:
            p = obj.pharmacist_profile
            pharmacy = getattr(p, 'pharmacy', None)
            return {
                'order_registration_number': p.order_registration_number,
                'cnas_coverage': p.cnas_coverage,
                'pharmacy_name': pharmacy.name if pharmacy else '',
                'agreement_number': pharmacy.agreement_number if pharmacy else '',
            }
        except Exception:
            return None

    def get_caretaker_detail(self, obj):
        if obj.role != 'caretaker':
            return None
        try:
            p = obj.caretaker_profile
            return {
                'experience_years': p.experience_years,
                'availability_area': p.availability_area,
                'tarif_de_base': str(p.tarif_de_base),
                'certification': p.certification,
                'is_verified': p.is_verified,
            }
        except Exception:
            return None

    def update(self, instance, validated_data):
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
