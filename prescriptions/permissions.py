from rest_framework.permissions import BasePermission

class IsPatient(BasePermission):
    """Accès réservé aux patients."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'patient')

class IsDoctor(BasePermission):
    """Accès réservé aux médecins."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'doctor')

class IsPharmacist(BasePermission):
    """Accès réservé aux pharmaciens."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'pharmacist')

class IsCaregiver(BasePermission):
    """Accès réservé aux gardes-malades."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'caregiver')

class IsPrescriptionOwner(BasePermission):
    """
    Vérifie si l'utilisateur est le propriétaire de l'ordonnance 
    (le médecin qui l'a créée ou le patient concerné).
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        role = getattr(request.user, 'role', None)
        if role == 'doctor':
            return obj.consultation.doctor.user == request.user
        if role == 'patient':
            return obj.consultation.patient.user == request.user
        if role == 'pharmacist':
            # Un pharmacien peut voir s'il a reçu une commande liée
            return obj.pharmacy_orders.filter(pharmacist=request.user).exists()
        if role == 'caregiver':
            # Un garde-malade peut voir s'il s'occupe du patient
            try:
                from caregiver.models import CaregiverAssignment
                return CaregiverAssignment.objects.filter(
                    caregiver=request.user, 
                    patient=obj.consultation.patient, 
                    is_active=True
                ).exists()
            except ImportError:
                return False
        return False

class IsCaregiverOfPatient(BasePermission):
    """Vérifie si le garde-malade est assigné au patient."""
    def has_object_permission(self, request, view, obj):
        if getattr(request.user, 'role', None) != 'caregiver':
            return False
        try:
            from caregiver.models import CaregiverAssignment
            # On suppose que obj a un attribut 'patient' ou passe par consultation
            patient = getattr(obj, 'patient', None)
            if not patient and hasattr(obj, 'consultation'):
                patient = obj.consultation.patient
            
            return CaregiverAssignment.objects.filter(
                caregiver=request.user, 
                patient=patient, 
                is_active=True
            ).exists()
        except (ImportError, AttributeError):
            return False

class IsPharmacyOrderOwner(BasePermission):
    """Vérifie si l'utilisateur est le patient ou le pharmacien de la commande."""
    def has_object_permission(self, request, view, obj):
        return obj.patient == request.user or obj.pharmacist == request.user