import json
from datetime import timedelta

from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Consultation
from .serializers import ConsultationSerializer
from appointments.models import Appointment
from appointments.permissions import IsDoctor
from prescriptions.models import Prescription, PrescriptionItem


# ── Mapping frontend frequency strings → PrescriptionItem.Frequency choices ──
_FREQUENCY_MAP = {
    "once daily":          PrescriptionItem.Frequency.ONCE_DAILY,
    "twice daily":         PrescriptionItem.Frequency.TWICE_DAILY,
    "three times daily":   PrescriptionItem.Frequency.THREE_DAILY,
    "as needed":           PrescriptionItem.Frequency.AS_NEEDED,
    "every 8h":            PrescriptionItem.Frequency.EVERY_8H,
    "1x_day":              PrescriptionItem.Frequency.ONCE_DAILY,
    "2x_day":              PrescriptionItem.Frequency.TWICE_DAILY,
    "3x_day":              PrescriptionItem.Frequency.THREE_DAILY,
    "every_8h":            PrescriptionItem.Frequency.EVERY_8H,
    "as_needed":           PrescriptionItem.Frequency.AS_NEEDED,
}

def _map_frequency(value):
    if not value:
        return PrescriptionItem.Frequency.ONCE_DAILY
    return _FREQUENCY_MAP.get(str(value).strip().lower(), PrescriptionItem.Frequency.ONCE_DAILY)


class ConsultationViewSet(viewsets.ModelViewSet):
    """
    Gestion des consultations.
    """
    queryset = Consultation.objects.select_related('doctor__user', 'patient__user', 'appointment').all()
    serializer_class = ConsultationSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsDoctor()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        consultation = serializer.save()
        if consultation.appointment:
            appointment = consultation.appointment
            appointment.status = 'completed'
            appointment.save()

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'role', None)

        if role == 'patient':
            return Consultation.objects.filter(patient__user=user)
        if role == 'doctor':
            return Consultation.objects.filter(doctor__user=user)
        if user.is_staff:
            return Consultation.objects.all()
        return Consultation.objects.none()


class CompleteSessionView(APIView):
    """
    POST /api/consultations/complete-session/

    Clôture une consultation : crée la Consultation, la Prescription
    et ses PrescriptionItems, génère le QRToken (via signal), marque
    le RDV comme terminé et notifie le patient.

    Body :
    {
      appointment_id: int,
      diagnosis: str,
      symptoms: str (optionnel),
      notes: str (optionnel),
      vitals: { blood_pressure, heart_rate, temperature, oxygen_saturation } (optionnel),
      prescriptions: [
        { drug_name|medication, dosage?, frequency, duration }
      ],
      lab_requests: [...] (ignoré pour l'instant)
    }

    Réponse : { consultation_id, prescription_id, prescription_qr_url, prescription_token }
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    def post(self, request):
        data = request.data or {}

        appointment_id = data.get('appointment_id')
        if not appointment_id:
            return Response({'detail': 'appointment_id requis.'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Récupère le RDV et vérifie l'appartenance au médecin connecté
        try:
            appointment = Appointment.objects.select_related(
                'doctor__user', 'patient__user'
            ).get(pk=appointment_id)
        except Appointment.DoesNotExist:
            return Response({'detail': 'Rendez-vous introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        doctor_profile = getattr(request.user, 'doctor_profile', None)
        if not doctor_profile or appointment.doctor_id != doctor_profile.id:
            return Response(
                {'detail': "Ce rendez-vous n'appartient pas au médecin connecté."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Si une consultation existe déjà pour ce RDV, on évite le doublon
        try:
            existing = appointment.consultation
        except Consultation.DoesNotExist:
            existing = None
        if existing is not None:
            return Response(
                {'detail': 'Une consultation existe déjà pour ce rendez-vous.',
                 'consultation_id': str(existing.id)},
                status=status.HTTP_409_CONFLICT,
            )

        diagnosis = (data.get('diagnosis') or '').strip()
        if not diagnosis:
            return Response({'detail': 'diagnosis requis.'}, status=status.HTTP_400_BAD_REQUEST)

        notes     = data.get('notes') or ''
        symptoms  = data.get('symptoms') or ''
        vitals    = data.get('vitals') or {}
        rx_items  = data.get('prescriptions') or []

        # 2. Création de la consultation
        consultation = Consultation.objects.create(
            doctor=appointment.doctor,
            patient=appointment.patient,
            appointment=appointment,
            chief_complaint=symptoms or appointment.motif or '—',
            diagnosis=diagnosis,
            doctor_notes=notes,
            vitals=json.dumps(vitals) if isinstance(vitals, dict) else str(vitals or ''),
            status=Consultation.Status.COMPLETED,
            consulted_at=timezone.now(),
        )

        # 3. Création de la prescription (le QRToken se crée via signal post_save)
        prescription = Prescription.objects.create(
            consultation=consultation,
            valid_until=(timezone.now() + timedelta(days=90)).date(),
            notes=notes,
        )

        # 4. Création des PrescriptionItems
        for item in rx_items:
            if not isinstance(item, dict):
                continue
            drug_name = (item.get('drug_name') or item.get('medication') or '').strip()
            if not drug_name:
                continue
            PrescriptionItem.objects.create(
                prescription=prescription,
                drug_name=drug_name,
                dosage=item.get('dosage') or '',
                frequency=_map_frequency(item.get('frequency')),
                duration=item.get('duration') or '',
                instructions=item.get('instructions') or '',
            )

        # 5. QR token : créé automatiquement par le signal post_save sur Prescription
        prescription.refresh_from_db()
        qr_token_obj = getattr(prescription, 'qr_token', None)
        token_str    = qr_token_obj.token if qr_token_obj else None
        qr_url       = request.build_absolute_uri(
            f'/api/prescriptions/{prescription.pk}/qr-image/'
        )

        # 6. Marque le RDV comme terminé
        appointment.complete(notes=notes)

        # 7. Notification patient
        try:
            from notifications.models import Notification
            Notification.objects.create(
                user=appointment.patient.user,
                title="Consultation terminée",
                message="Votre consultation est terminée. Une ordonnance a été générée.",
                notification_type=Notification.NotificationType.APPOINTMENT,
            )
        except Exception:
            pass

        # 8. Réponse
        return Response(
            {
                'consultation_id':     str(consultation.id),
                'prescription_id':     str(prescription.id),
                'prescription_qr_url': qr_url,
                'prescription_token':  token_str,
            },
            status=status.HTTP_201_CREATED,
        )
