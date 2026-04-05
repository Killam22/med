from rest_framework import viewsets, permissions
from .models import Consultation
from .serializers import ConsultationSerializer
from appointments.permissions import IsDoctor

class ConsultationViewSet(viewsets.ModelViewSet):
    """
    Gestion des consultations.
    """
    queryset = Consultation.objects.select_related('doctor__user', 'patient__user', 'appointment').all()
    serializer_class = ConsultationSerializer
    permission_classes = [IsDoctor]

    def perform_create(self, serializer):
        consultation = serializer.save()
        # Mettre à jour le statut du RDV à 'Terminé' si présent
        if consultation.appointment:
            appointment = consultation.appointment
            appointment.status = 'completed'
            appointment.save()
            # print(f"DEBUG: Appointment {appointment.id} set to completed.")

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'role', None)

        if role == 'patient':
            # Utilise patient_profile pour plus de sécurité si possible
            return Consultation.objects.filter(patient__user=user)
        
        if role == 'doctor':
            return Consultation.objects.filter(doctor__user=user)

        if user.is_staff:
            return Consultation.objects.all()

        return Consultation.objects.none()
