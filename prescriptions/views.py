import base64
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Prescription, QRToken
from .serializers import (
    PrescriptionSerializer,
    PrescriptionCreateSerializer,
)
from .permissions import IsDoctor, IsPharmacist, IsPrescriptionOwner
from .services import QRCodeService, CNASService, PDFService


class PrescriptionViewSet(viewsets.ModelViewSet):
    """
    CRUD complet sur les ordonnances.
    GET    /api/prescriptions/        → liste (filtrée par rôle)
    POST   /api/prescriptions/        → créer (docteur seulement)
    GET    /api/prescriptions/<id>/   → détail
    DELETE /api/prescriptions/<id>/   → annuler
    POST   /api/prescriptions/<id>/qr/      → générer/récupérer le QR
    POST   /api/prescriptions/<id>/pdf/     → télécharger le PDF
    POST   /api/prescriptions/<id>/cnas/    → vérifier couverture
    """

    def get_serializer_class(self):
        if self.action == 'create':
            return PrescriptionCreateSerializer
        return PrescriptionSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsDoctor()]
        if self.action == 'destroy':
            return [IsAuthenticated(), IsDoctor()]
        return [IsAuthenticated(), IsPrescriptionOwner()]

    def get_queryset(self):
        user = self.request.user
        qs   = Prescription.objects.select_related(
            'consultation__doctor',
            'consultation__patient',
            'qr_token',
            'cnas_coverage'
        ).prefetch_related('items')

        role = getattr(user, 'role', None)

        if role == 'doctor':
            qs = qs.filter(consultation__doctor__user=user)
            patient_id = self.request.query_params.get('patient')
            if patient_id:
                qs = qs.filter(consultation__patient_id=patient_id)
            return qs
        if role == 'patient':
            return qs.filter(consultation__patient__user=user)
        if role == 'pharmacist':
            return qs.filter(pharmacy_orders__pharmacist=user).distinct()
        if role == 'caregiver':
            try:
                from caregiver.models import CaregiverAssignment
                patient_ids = CaregiverAssignment.objects.filter(
                    caregiver=user, is_active=True
                ).values_list('patient_id', flat=True)
                return qs.filter(consultation__patient_id__in=patient_ids)
            except Exception:
                return qs.none()
        if user.is_staff:
            return qs.all()
        return qs.none()

    def destroy(self, request, *args, **kwargs):
        """Annuler (pas supprimer) une ordonnance."""
        prescription = self.get_object()
        prescription.status = Prescription.Status.CANCELLED
        prescription.save()
        return Response({'detail': 'Ordonnance annulée.'})

    @action(detail=True, methods=['get'], url_path='qr')
    def qr_code(self, request, pk=None):
        """Retourne le QR en JSON base64. Pour l'image PNG directe, voir /api/prescriptions/{id}/qr-image/"""
        prescription = self.get_object()
        qr_token     = getattr(prescription, 'qr_token', None)

        if not qr_token:
            return Response({'error': 'QR token introuvable.'}, status=404)

        qr_base64 = QRCodeService.generate_qr_image(qr_token.token)
        return Response({
            'qr_base64': qr_base64,
            'token':     qr_token.token,
            'expires_at': qr_token.expires_at,
            'is_valid':  qr_token.is_valid(),
            'image_url': request.build_absolute_uri(f'/api/prescriptions/{prescription.pk}/qr-image/'),
        })

    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf_export(self, request, pk=None):
        """Télécharge l'ordonnance en PDF."""
        prescription = self.get_object()
        pdf_bytes    = PDFService.generate(prescription)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'inline; filename="ordonnance-{str(prescription.id)[:8]}.pdf"'
        )
        return response

    
    @action(detail=False, methods=['get'], url_path='caregiver-patients')
    def caregiver_patients_prescriptions(self, request):
        """
        GET /api/prescriptions/caregiver-patients/
        Garde-malade : liste des ordonnances de ses patients assignés.
        """
        if getattr(request.user, 'role', None) != 'caretaker':
            return Response({'error': 'Accès réservé aux gardes-malades.'}, status=403)

        try:
            from caregiver.models import CaregiverAssignment
            patient_ids = CaregiverAssignment.objects.filter(
                caregiver=request.user, is_active=True
            ).values_list('patient_id', flat=True)
        except Exception:
            return Response({'error': 'Module caregiver introuvable.'}, status=500)

        prescriptions = Prescription.objects.filter(
            consultation__patient_id__in=patient_ids,
            status=Prescription.Status.ACTIVE
        ).select_related(
            'consultation__doctor__user',
            'consultation__patient__user',
            'qr_token',
        ).prefetch_related('items')

        serializer = PrescriptionSerializer(prescriptions, many=True)
        return Response(serializer.data)    

    @action(detail=True, methods=['post'], url_path='cnas')
    def cnas_verify(self, request, pk=None):
        """Calcule la couverture CNAS pour cette ordonnance."""
        prescription = self.get_object()
        cnas_number  = request.data.get('cnas_number')
        category     = request.data.get('category', 'general')

        if not cnas_number:
            return Response(
                {'error': 'cnas_number est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        coverage = CNASService.calculate_coverage(prescription, cnas_number, category)
        return Response({
            'cnas_number':     coverage.cnas_number,
            'coverage_rate':   f"{coverage.coverage_rate}%",
            'original_amount': f"{coverage.original_amount} DZD",
            'covered_amount':  f"{coverage.covered_amount} DZD",
            'patient_pays':    f"{coverage.patient_pays} DZD",
            'status':          coverage.status,
        })


class QuickPrescriptionView(APIView):
    """
    POST /api/prescriptions/quick/
    Médecin : crée une ordonnance "rapide" sans rendez-vous parent.

    Body (patient avec compte) :
    {
      "patient_id": <int>,
      "chief_complaint": "Renouvellement",
      "notes": "...",
      "valid_until": "2026-07-30",
      "items": [{"drug_name": "Metformin", "dosage": "500mg", "frequency": "2x_day", "duration": "30 jours"}]
    }

    Body (patient sans compte) :
    {
      "external_patient_id": <int>,
      "chief_complaint": "Ordonnance rapide",
      "notes": "...",
      "items": [...]
    }
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    def post(self, request):
        from datetime import timedelta, date
        from django.utils import timezone
        from consultations.models import Consultation
        from patients.models import Patient, ExternalPatient
        from notifications.models import Notification

        patient_id          = request.data.get('patient_id')
        external_patient_id = request.data.get('external_patient_id')
        items_data          = request.data.get('items') or []

        if not patient_id and not external_patient_id:
            return Response({'error': 'patient_id ou external_patient_id est requis.'}, status=400)
        if not items_data:
            return Response({'error': 'Au moins un médicament est requis.'}, status=400)

        for i, it in enumerate(items_data):
            name = (it.get('drug_name') or it.get('medication') or '').strip()
            if not name:
                return Response(
                    {'error': f'Le nom du médicament est obligatoire (ligne {i + 1}).'},
                    status=400,
                )

        doctor = request.user.doctor_profile
        chief  = request.data.get('chief_complaint') or 'Ordonnance rapide'
        notes  = request.data.get('notes') or ''
        valid_until = request.data.get('valid_until')
        if not valid_until:
            valid_until = timezone.now().date() + timedelta(days=90)
        elif isinstance(valid_until, str):
            try:
                valid_until = date.fromisoformat(valid_until)
            except ValueError:
                return Response(
                    {'error': 'valid_until doit être une date au format YYYY-MM-DD.'},
                    status=400,
                )
        elif not isinstance(valid_until, date):
            return Response(
                {'error': 'valid_until doit être une date.'},
                status=400,
            )

        patient          = None
        external_patient = None

        if patient_id:
            try:
                patient = Patient.objects.get(pk=patient_id)
            except Patient.DoesNotExist:
                return Response({'error': 'Patient introuvable.'}, status=404)
        else:
            try:
                external_patient = ExternalPatient.objects.get(pk=external_patient_id, doctor=doctor)
            except ExternalPatient.DoesNotExist:
                return Response({'error': 'Patient externe introuvable.'}, status=404)

        consultation = Consultation.objects.create(
            doctor=doctor,
            patient=patient,
            external_patient=external_patient,
            consultation_type=Consultation.ConsultationType.IN_PERSON,
            status=Consultation.Status.COMPLETED,
            chief_complaint=chief,
            consulted_at=timezone.now(),
        )

        prescription = Prescription.objects.create(
            consultation=consultation,
            notes=notes,
            valid_until=valid_until,
        )

        from .models import PrescriptionItem
        for it in items_data:
            PrescriptionItem.objects.create(
                prescription=prescription,
                drug_name=it.get('drug_name', '') or it.get('medication', ''),
                molecule=it.get('molecule', ''),
                dosage=it.get('dosage', ''),
                frequency=it.get('frequency', '1x_day'),
                duration=it.get('duration', ''),
                instructions=it.get('instructions', ''),
                quantity=int(it.get('quantity', 1)),
            )

        # Notifier uniquement les patients avec un compte
        if patient:
            Notification.objects.create(
                user=patient.user,
                title="Nouvelle ordonnance",
                message=f"Le Dr. {doctor.user.last_name} vient de vous délivrer une ordonnance.",
                notification_type=Notification.NotificationType.SYSTEM,
            )

        return Response(PrescriptionSerializer(prescription).data, status=status.HTTP_201_CREATED)


class QRScanView(APIView):
    """
    POST /api/prescriptions/scan/
    Body: { "token": "..." }
    Utilisé par le pharmacien pour scanner une ordonnance.
    """
    permission_classes = [IsAuthenticated, IsPharmacist]

    # Nécessaire pour que l'interface DRF affiche le bon formulaire
    def get_serializer(self, *args, **kwargs):
        from .serializers import QRScanSerializer
        return QRScanSerializer(*args, **kwargs)

    def post(self, request):
        from .serializers import QRScanSerializer
        serializer = QRScanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token = serializer.validated_data['token']
        result = QRCodeService.validate_and_scan(token, request.user)

        if not result['valid']:
            return Response(
                {'error': result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )

        prescription_serializer = PrescriptionSerializer(result['prescription'])
        return Response({
            'message': 'QR code validé avec succès.',
            'prescription': prescription_serializer.data,
        })







# ── Vues standalone (hors DRF) pour le rendu direct navigateur ───────────────

class QRImageView(APIView):
    """
    GET /api/prescriptions/{uuid}/qr-image/
    Retourne directement l'image QR en PNG — affichable dans un <img> ou navigateur.
    Bypasse le content-negotiation DRF qui forcerait un rendu JSON.
    """
    permission_classes = [IsAuthenticated, IsPrescriptionOwner]

    def get(self, request, pk):
        print(f"DEBUG: QRImageView pour {pk}")
        from .models import Prescription
        prescription = get_object_or_404(Prescription, pk=pk)
        self.check_object_permissions(request, prescription)
        
        qr_token = getattr(prescription, 'qr_token', None)
        if not qr_token:
            return HttpResponse("QR token introuvable.", status=404, content_type="text/plain")

        qr_base64  = QRCodeService.generate_qr_image(qr_token.token)
        image_data = base64.b64decode(qr_base64)
        return HttpResponse(image_data, content_type="image/png")


class PrescriptionPDFView(APIView):
    """
    GET /api/prescriptions/{uuid}/pdf-download/
    Retourne directement le PDF — téléchargeable dans le navigateur.
    """
    permission_classes = [IsAuthenticated, IsPrescriptionOwner]

    def get(self, request, pk):
        from .models import Prescription
        prescription = get_object_or_404(Prescription, pk=pk)
        self.check_object_permissions(request, prescription)
        
        try:
            pdf_bytes = PDFService.generate(prescription)
            response  = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = (
                f'attachment; filename="ordonnance-{str(prescription.id)[:8]}.pdf"'
            )
            return response
        except Exception as e:
            print(f"DEBUG ERROR PDF: {e}")
            return HttpResponse(f"Erreur génération PDF: {e}", status=500)
