import io
import base64
from django.utils import timezone
from .models import QRToken, CNASCoverage
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import cm

try:
    import qrcode
except ImportError:
    qrcode = None

class QRCodeService:
    @staticmethod
    def generate_qr_image(token_str):
        if not qrcode:
            return "QR Code Library not installed"
            
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(token_str)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    @staticmethod
    def validate_and_scan(token_str, user):
        try:
            qr_token = QRToken.objects.get(token=token_str)
            if not qr_token.is_valid():
                return {'valid': False, 'error': 'Token expiré ou déjà utilisé.'}
            
            # Marquer comme utilisé
            qr_token.is_used = True
            qr_token.scanned_by = user
            qr_token.scanned_at = timezone.now()
            qr_token.save()
            
            return {'valid': True, 'prescription': qr_token.prescription}
        except QRToken.DoesNotExist:
            return {'valid': False, 'error': 'Token invalide.'}

class CNASService:
    @staticmethod
    def calculate_coverage(prescription, cnas_number, category='general'):
        """Simulation du calcul de remboursement CNAS."""
        # Logique simplifiée : 80% pour chronique, 20% sinon
        coverage_rate = 80.0 if category == 'chronic' else 20.0
        
        # On calcule sur un montant fictif basé sur les items
        original_amount = sum([100.0 * item.quantity for item in prescription.items.all()])
        if original_amount == 0: original_amount = 1000.0
        
        covered_amount = (original_amount * coverage_rate) / 100
        patient_pays = original_amount - covered_amount
        
        coverage, created = CNASCoverage.objects.update_or_create(
            prescription=prescription,
            defaults={
                'cnas_number': cnas_number,
                'coverage_rate': coverage_rate,
                'original_amount': original_amount,
                'covered_amount': covered_amount,
                'patient_pays': patient_pays,
                'status': CNASCoverage.CoverageStatus.APPROVED,
                'verified_at': timezone.now()
            }
        )
        return coverage

class PDFService:
    @staticmethod
    def generate(prescription):
        """Génère un véritable PDF pour l'ordonnance."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        
        # Styles personnalisés
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=22,
            alignment=1, # Center
            spaceAfter=20,
            textColor=colors.HexColor("#2C3E50")
        )
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=10,
            textColor=colors.grey
        )
        
        content = []

        # 1. En-tête : Nom du Docteur et de la Clinique
        doctor = prescription.consultation.doctor
        content.append(Paragraph(f"<b>Docteur {doctor.user.get_full_name()}</b>", styles['Heading2']))
        content.append(Paragraph(f"{getattr(doctor, 'specialty', 'Médecin Généraliste')}", styles['Normal']))
        content.append(Spacer(1, 0.5*cm))
        
        # 2. Titre de l'ordonnance
        content.append(Paragraph("ORDONNANCE MÉDICALE", title_style))
        content.append(Paragraph(f"Date : {prescription.created_at.strftime('%d/%m/%Y')}", styles['Normal']))
        content.append(Paragraph(f"Référence : RX-{str(prescription.id)[:8].upper()}", subtitle_style))
        content.append(Spacer(1, 1*cm))

        # 3. Informations Patient
        patient = prescription.consultation.patient
        content.append(Paragraph(f"<b>Patient :</b> {patient.user.get_full_name()}", styles['Normal']))
        content.append(Spacer(1, 1*cm))

        # 4. Liste des Médicaments (Tableau)
        data = [['Médicament', 'Posologie', 'Durée']]
        for item in prescription.items.all():
            data.append([
                f"{item.drug_name} {item.dosage}\n({item.molecule})" if item.molecule else f"{item.drug_name} {item.dosage}",
                item.get_frequency_display(),
                item.duration
            ])
        
        table = Table(data, colWidths=[8*cm, 5*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F2F3F4")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        content.append(table)
        content.append(Spacer(1, 1.5*cm))

        # 5. Notes éventuelles
        if prescription.notes:
            content.append(Paragraph("<b>Notes :</b>", styles['Normal']))
            content.append(Paragraph(prescription.notes, styles['Normal']))
            content.append(Spacer(1, 1*cm))

        # 6. QR Code en bas à droite
        qr_token = getattr(prescription, 'qr_token', None)
        if qr_token:
            qr_base64 = QRCodeService.generate_qr_image(qr_token.token)
            qr_data = base64.b64decode(qr_base64)
            qr_image = Image(io.BytesIO(qr_data), 3*cm, 3*cm)
            qr_image.hAlign = 'RIGHT'
            content.append(qr_image)
            content.append(Paragraph("Scannez pour vérification", ParagraphStyle('QRNote', parent=styles['Normal'], fontSize=8, alignment=2)))

        # Construction du document
        doc.build(content)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes