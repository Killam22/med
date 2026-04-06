
import uuid
from django.db import models

class Medication(models.Model):
    """Registre global et centralisé de tous les médicaments de la plateforme"""

    class Category(models.TextChoices):
        CARDIO      = 'cardio',      'Cardiologie'
        DIABETES    = 'diabetes',    'Diabétologie'
        ANTIBIOTIC  = 'antibiotic',  'Antibiotique'
        ANALGESIC   = 'analgesic',   'Analgésique'
        ANTI_INFLAM = 'anti_inflam', 'Anti-inflammatoire'
        GASTRO      = 'gastro',      'Gastro-entérologie'
        NEURO       = 'neuro',       'Neurologie'
        OTHER       = 'other',       'Autre'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name         = models.CharField(max_length=250, unique=True)
    molecule     = models.CharField(max_length=250, blank=True, help_text="Principe actif")
    category     = models.CharField(max_length=30, choices=Category.choices, default=Category.OTHER)
    description  = models.TextField(blank=True)
    
    barcode      = models.CharField(max_length=100, unique=True, null=True, blank=True)
    form         = models.CharField(max_length=250, blank=True, help_text="Ex: Sirop, Comprimé, Pommade")
    dosage_forms = models.JSONField(default=list, help_text='Ex: ["500mg", "1g"]') 
    
    side_effects = models.TextField(blank=True)
    interactions = models.TextField(blank=True)
    contraindications = models.TextField(blank=True)
    
    price_dzd    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Prix de référence")
    cnas_covered = models.BooleanField(default=False)
    is_shifa_compatible = models.BooleanField(default=False)
    requires_prescription = models.BooleanField(default=True)
    
    manufacturer = models.CharField(max_length=250, blank=True)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Médicament (Référence)"
        verbose_name_plural = "Médicaments (Références)"

    def __str__(self):
        return f"{self.name} ({self.form}) - {self.molecule}"