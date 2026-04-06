from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from django.db.models import Sum, Count
from rest_framework.renderers import JSONRenderer

from django.contrib.auth import get_user_model
from appointments.models import Appointment
from consultations.models import Consultation
from pharmacy.models import PharmacyOrder, PharmacyStock
from caretaker.models import CareRequest
from notifications.models import Notification

User = get_user_model()


class PatientDashboardView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]

    def get(self, request):
        if getattr(request.user, 'role', None) != 'patient':
            return Response({"error": "Accès refusé"}, status=status.HTTP_403_FORBIDDEN)

        user = request.user
        today = timezone.now().date()

        upcoming_appts = Appointment.objects.filter(
            patient__user=user, date__gte=today, status__in=['scheduled', 'pending', 'confirmed']
        ).order_by('date', 'start_time')[:3]

        notifications = Notification.objects.filter(user=user, is_read=False).order_by('-created_at')[:5]
        recent_docs = Consultation.objects.filter(patient__user=user).order_by('-created_at')[:3]
        active_orders = PharmacyOrder.objects.filter(patient=user).exclude(status__in=['completed', 'cancelled'])
        active_care = CareRequest.objects.filter(patient=user, status='accepted').first()

        data = {
            "upcoming_appointments": [
                {
                    "id": str(a.id),
                    "date": a.date.isoformat(),
                    "start_time": a.start_time.strftime('%H:%M'),
                    "end_time": a.end_time.strftime('%H:%M'),
                    "doctor": a.doctor.user.get_full_name(),
                    "specialty": a.doctor.specialty,
                    "status": a.status,
                }
                for a in upcoming_appts
            ],
            "notifications": [
                {"id": n.id, "title": n.title, "message": n.message, "type": n.notification_type}
                for n in notifications
            ],
            "recent_documents": [
                {
                    "date": d.created_at.date(),
                    "doctor": f"Dr. {d.doctor.user.last_name}",
                }
                for d in recent_docs
            ],
            "prescription_status": [
                {"id": str(o.id), "status": o.status}
                for o in active_orders
            ],
            "caregiver": active_care.caretaker.user.get_full_name() if active_care else None,
        }
        return Response(data)


class DoctorDashboardView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]

    def get(self, request):
        if getattr(request.user, 'role', None) != 'doctor':
            return Response({"error": "Accès refusé"}, status=status.HTTP_403_FORBIDDEN)

        user = request.user
        today = timezone.now().date()

        today_appointments = Appointment.objects.filter(doctor__user=user, date=today)
        pending_appointments = Appointment.objects.filter(doctor__user=user, status='pending')

        data = {
            "kpis": {
                "today_consultations": today_appointments.exclude(status='cancelled').count(),
                "total_patients": Appointment.objects.filter(
                    doctor__user=user
                ).values('patient').distinct().count(),
                "pending_requests": pending_appointments.count(),
            },
            "todays_schedule": [
                {
                    "id": str(a.id),
                    "start_time": a.start_time.strftime('%H:%M'),
                    "end_time": a.end_time.strftime('%H:%M'),
                    "patient_name": a.patient.user.get_full_name(),
                    "motif": a.motif,
                    "status": a.status,
                }
                for a in today_appointments.exclude(status='cancelled').order_by('start_time')
            ],
            "patient_requests": [
                {
                    "id": str(a.id),
                    "patient_name": a.patient.user.get_full_name(),
                    "date": a.date.isoformat(),
                    "start_time": a.start_time.strftime('%H:%M'),
                    "motif": a.motif,
                }
                for a in pending_appointments.order_by('date')
            ],
        }
        return Response(data)


class PharmacistDashboardView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]

    def get(self, request):
        if getattr(request.user, 'role', None) != 'pharmacist':
            return Response({"error": "Accès refusé"}, status=status.HTTP_403_FORBIDDEN)

        user = request.user
        today = timezone.now().date()
        today_orders = PharmacyOrder.objects.filter(pharmacist=user, created_at__date=today)
        stock_alerts = PharmacyStock.objects.filter(pharmacist__user=user, quantity__lt=10)

        revenue_dict = today_orders.filter(status='delivered').aggregate(total=Sum('total_price'))
        today_revenue = revenue_dict['total'] or 0

        data = {
            "kpis": {
                "today_orders": today_orders.count(),
                "today_revenue": float(today_revenue),
                "stock_items": PharmacyStock.objects.filter(pharmacist__user=user).count(),
                "stock_alerts_count": stock_alerts.count(),
            },
            "priority_alerts": [
                {
                    "type": "stock",
                    "message": f"{s.medication.name} - Stock critique ({s.quantity} unités)",
                }
                for s in stock_alerts
            ],
            "recent_orders": [
                {
                    "id": str(o.id),
                    "patient": o.patient.get_full_name(),
                    "status": o.status,
                    "created_at": o.created_at,
                }
                for o in PharmacyOrder.objects.filter(pharmacist=user).order_by('-created_at')[:5]
            ],
        }
        return Response(data)


class CaretakerDashboardView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]

    def get(self, request):
        if getattr(request.user, 'role', None) != 'caretaker':
            return Response({"error": "Accès refusé"}, status=status.HTTP_403_FORBIDDEN)

        user = request.user
        my_requests = CareRequest.objects.filter(caretaker__user=user, status='accepted')

        data = {
            "my_patients": [
                {
                    "name": r.patient.get_full_name(),
                    "start_date": r.start_date,
                    "end_date": r.end_date,
                }
                for r in my_requests
            ],
            "pending_requests": CareRequest.objects.filter(
                caretaker__user=user, status='pending'
            ).count(),
        }
        return Response(data)


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer]

    def get(self, request):
        if getattr(request.user, 'role', None) != 'admin' and not request.user.is_superuser:
            return Response({"error": "Accès refusé"}, status=status.HTTP_403_FORBIDDEN)

        users = User.objects.all()
        role_counts = users.values('role').annotate(count=Count('id'))
        distribution = {item['role']: item['count'] for item in role_counts}

        data = {
            "kpis": {
                "total_users": users.count(),
                "verified_doctors": users.filter(role='doctor', verification_status='verified').count(),
                "active_pharmacies": users.filter(role='pharmacist').count(),
                "total_appointments": Appointment.objects.count(),
            },
            "role_distribution": distribution,
            "recent_registrations": [
                {
                    "name": u.get_full_name() or u.username or u.email,
                    "role": u.role,
                    "date": u.date_joined.date(),
                }
                for u in users.order_by('-date_joined')[:5]
            ],
        }
        return Response(data)