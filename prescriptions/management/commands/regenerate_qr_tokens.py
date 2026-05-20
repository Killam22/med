"""
python manage.py regenerate_qr_tokens

Regenere les QR tokens pour toutes les ordonnances dont le token est :
  - manquant
  - expire
  - deja utilise (is_used=True)
  - sans signature numerique valide

Options :
  --dry-run   : affiche ce qui serait fait sans rien modifier
  --force-all : regenere TOUS les tokens, meme les valides
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from prescriptions.models import Prescription, QRToken


class Command(BaseCommand):
    help = "Regenere les QR tokens invalides ou manquants pour toutes les ordonnances."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche les actions sans les executer.",
        )
        parser.add_argument(
            "--force-all",
            action="store_true",
            help="Regenere tous les tokens, meme les valides.",
        )

    def handle(self, *args, **options):
        dry_run   = options["dry_run"]
        force_all = options["force_all"]
        now       = timezone.now()

        prescriptions = Prescription.objects.prefetch_related("qr_token").all()
        total = prescriptions.count()
        self.stdout.write(f"-> {total} ordonnance(s) trouvee(s).\n")

        created     = 0
        regenerated = 0
        skipped     = 0

        for rx in prescriptions:
            qr = getattr(rx, "qr_token", None)
            reason = None

            if qr is None:
                reason = "aucun token"
            elif force_all:
                reason = "force-all"
            elif qr.is_used:
                reason = "deja utilise"
            elif qr.expires_at <= now:
                reason = "expire"
            elif not qr.digital_signature:
                reason = "signature manquante"

            if reason is None:
                skipped += 1
                continue

            label = f"RX-{str(rx.id)[:8].upper()}"

            if dry_run:
                self.stdout.write(f"  [DRY-RUN] {label} -> serait regenere ({reason})")
                regenerated += 1
                continue

            if qr is not None:
                qr.delete()
                regenerated += 1
            else:
                created += 1

            QRToken.objects.create(prescription=rx)
            self.stdout.write(self.style.SUCCESS(f"  OK {label} ({reason}) -> nouveau QR genere"))

        self.stdout.write("\n-- Resume --")
        if dry_run:
            self.stdout.write(f"  A regenerer : {regenerated}")
            self.stdout.write(f"  Valides     : {skipped}")
            self.stdout.write("  (aucune modification -- mode dry-run)")
        else:
            self.stdout.write(self.style.SUCCESS(f"  Crees      : {created}"))
            self.stdout.write(self.style.SUCCESS(f"  Regeneres  : {regenerated}"))
            self.stdout.write(f"  Inchanges  : {skipped}")
        self.stdout.write("------------\n")
