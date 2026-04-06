from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from appointments.models import Appointment
from notifications.models import Notification

class Command(BaseCommand):
    help = 'Envoie un rappel de rendez-vous aux patients 24h à l\'avance'

    def handle(self, *args, **kwargs):
        # On cherche les RDV confirmés qui ont lieu demain
        tomorrow = timezone.now().date() + timedelta(days=1)
        
        appointments = Appointment.objects.filter(
            status='confirmed',
            date=tomorrow
        )
        
        count = 0
        for appt in appointments:
            # Vérifier si on n'a pas déjà envoyé de rappel
            already_sent = Notification.objects.filter(
                user=appt.patient.user,
                notification_type=Notification.NotificationType.APPOINTMENT,
                title="Rappel de rendez-vous",
                created_at__date=timezone.now().date()
            ).exists()

            if not already_sent:
                Notification.objects.create(
                    user=appt.patient.user,
                    title="Rappel de rendez-vous",
                    message=f"Rappel : Vous avez un rendez-vous demain avec le Dr. {appt.doctor.user.last_name} à {appt.start_time.strftime('%H:%M')}.",
                    notification_type=Notification.NotificationType.APPOINTMENT
                )
                count += 1
                
        self.stdout.write(self.style.SUCCESS(f'{count} rappels envoyés.'))
