# diagnostic_ai/models.py

from django.db import models
from django.conf import settings
import os


# ══════════════════════════════════════════════════════════════
# INTERACTION — chaque échange patient ↔ bot IA
# ══════════════════════════════════════════════════════════════

class Interaction(models.Model):

    class Lang(models.TextChoices):
        FR = "fr", "Français"
        AR = "ar", "Arabe"
        EN = "en", "English"

    class Urgency(models.TextChoices):
        LOW    = "faible", "Faible"
        MEDIUM = "modere", "Modéré"
        HIGH   = "urgent", "Urgent"

    # ── Lien vers le vrai Patient du backend ─────────────────
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete    = models.CASCADE,
        related_name = 'ai_interactions',
        null         = True,
        blank        = True,
    )

    # ── Contenu de l'interaction ──────────────────────────────
    symptoms               = models.TextField()
    response               = models.TextField()
    lang                   = models.CharField(max_length=5, choices=Lang.choices, default=Lang.FR)
    urgency                = models.CharField(max_length=20, choices=Urgency.choices, default=Urgency.MEDIUM)
    specialist             = models.CharField(max_length=100, blank=True)

    # ── Médecin recommandé par le bot ─────────────────────────
    recommended_doctor = models.ForeignKey(
        'doctors.Doctor',
        on_delete    = models.SET_NULL,
        null         = True,
        blank        = True,
        related_name = 'ai_recommendations',
    )

    # ── Recommandation & feedback ─────────────────────────────
    feedback               = models.IntegerField(null=True, blank=True)
    pending_recommendation = models.TextField(null=True, blank=True)
    recommendation_sent    = models.BooleanField(default=False)
    from_cache             = models.BooleanField(default=False)
    created_at             = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering     = ["-created_at"]
        verbose_name = "Interaction IA"

    def __str__(self):
        name = self.patient.user.get_full_name() if self.patient else "Anonyme"
        return f"[{self.lang}] {name} — {self.symptoms[:50]}"


# ══════════════════════════════════════════════════════════════
# FICHIERS UPLOADÉS PAR LE PATIENT
# ══════════════════════════════════════════════════════════════

def upload_path(instance, filename):
    from django.utils import timezone
    now = timezone.now()
    patient_id = instance.patient.id if instance.patient else "anonymous"
    return os.path.join(
        "ai_uploads",
        str(patient_id),
        str(now.year),
        str(now.month).zfill(2),
        str(now.day).zfill(2),
        filename,
    )


class FileUpload(models.Model):

    class FileType(models.TextChoices):
        ORDONNANCE   = "ordonnance",   "Ordonnance"
        ANALYSE      = "analyse",      "Analyse médicale"
        RADIO        = "radio",        "Radio / IRM / Scanner"
        MEDICAMENT   = "medicament",   "Médicament"
        COMPTE_RENDU = "compte_rendu", "Compte rendu"
        GENERAL      = "general",      "Document général"

    interaction = models.OneToOneField(
        Interaction,
        on_delete    = models.SET_NULL,
        null         = True,
        blank        = True,
        related_name = "file_upload",
    )
    patient       = models.ForeignKey(
        'patients.Patient',
        on_delete    = models.CASCADE,
        related_name = 'ai_file_uploads',
        null         = True,
        blank        = True,
    )
    file          = models.FileField(upload_to=upload_path)
    original_name = models.CharField(max_length=255)
    mime_type     = models.CharField(max_length=100)
    file_type     = models.CharField(max_length=20, choices=FileType.choices, default=FileType.GENERAL)
    file_size     = models.IntegerField(default=0)
    user_message  = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering     = ["-created_at"]
        verbose_name = "Fichier médical IA"

    def __str__(self):
        name = self.patient.user.get_full_name() if self.patient else "Anonyme"
        return f"[{self.file_type}] {name} — {self.original_name}"

    @property
    def file_size_kb(self):
        return round(self.file_size / 1024, 1)

    @property
    def is_image(self):
        return self.mime_type.startswith("image/")

    @property
    def is_pdf(self):
        return self.mime_type == "application/pdf"


# ══════════════════════════════════════════════════════════════
# SESSION DE CONVERSATION
# ══════════════════════════════════════════════════════════════

class ConversationSession(models.Model):

    patient = models.ForeignKey(
        'patients.Patient',
        on_delete    = models.CASCADE,
        related_name = 'ai_sessions',
        null         = True,
        blank        = True,
    )
    lang       = models.CharField(max_length=5, default="fr")
    title      = models.CharField(max_length=200, blank=True)
    history    = models.JSONField(default=list)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering     = ["-updated_at"]
        verbose_name = "Session de conversation IA"

    def __str__(self):
        name = self.patient.user.get_full_name() if self.patient else "Anonyme"
        return f"Session {name} — {self.title or 'Sans titre'} ({self.message_count} msgs)"

    @property
    def message_count(self):
        return len(self.history)

    @property
    def last_message(self):
        if self.history:
            return self.history[-1].get("content", "")[:80]
        return ""

    def add_message(self, role: str, content: str, msg_type: str = "text", file_id: int = None):
        from django.utils import timezone
        entry = {
            "role":      role,
            "content":   content,
            "type":      msg_type,
            "timestamp": timezone.now().isoformat(),
        }
        if file_id:
            entry["file_id"] = file_id
        self.history.append(entry)
        self.save(update_fields=["history", "updated_at"])

    def get_gemini_history(self):
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self.history
            if m.get("content")
        ]

    def auto_title(self):
        for msg in self.history:
            if msg.get("role") == "user" and msg.get("content"):
                self.title = msg["content"][:60]
                self.save(update_fields=["title"])
                return self.title
        return "Nouvelle conversation"


# ══════════════════════════════════════════════════════════════
# CACHE DIAGNOSTICS
# ══════════════════════════════════════════════════════════════

class DiagnosisCache(models.Model):

    symptoms_hash  = models.CharField(max_length=64, unique=True, db_index=True)
    symptoms_text  = models.TextField()
    symptoms_en    = models.TextField()
    lang           = models.CharField(max_length=5, default="fr")
    response       = models.TextField()
    recommendation = models.TextField()
    diseases       = models.JSONField(default=list)
    specialist     = models.JSONField(default=dict)
    urgency        = models.CharField(max_length=20, default="modéré")
    hit_count      = models.IntegerField(default=1)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering     = ["-hit_count", "-created_at"]
        verbose_name = "Cache diagnostic"

    def __str__(self):
        return f"Cache: {self.symptoms_text[:50]} ({self.hit_count} hits)"


class QuestionCache(models.Model):

    question_hash = models.CharField(max_length=64, unique=True, db_index=True)
    question_text = models.TextField()
    lang          = models.CharField(max_length=5, default="fr")
    response      = models.TextField()
    intent        = models.CharField(max_length=20, default="question")
    hit_count     = models.IntegerField(default=1)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering     = ["-hit_count", "-created_at"]
        verbose_name = "Cache question"

    def __str__(self):
        return f"[{self.lang}] {self.question_text[:60]} ({self.hit_count} hits)"


# ══════════════════════════════════════════════════════════════
# TRAINING DATA & GENETIC RUN
# ══════════════════════════════════════════════════════════════

class TrainingData(models.Model):

    symptoms       = models.TextField()
    ideal_response = models.TextField()
    diseases       = models.JSONField(default=list)
    specialist     = models.CharField(max_length=100)
    urgency        = models.CharField(max_length=20)
    lang           = models.CharField(max_length=5)
    quality_score  = models.FloatField(default=1.0)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ["-quality_score", "-created_at"]
        verbose_name = "Donnée d'entraînement"

    def __str__(self):
        return f"Training: {self.symptoms[:50]}"


class GeneticRun(models.Model):

    generation      = models.IntegerField()
    best_fitness    = models.FloatField()
    best_chromosome = models.JSONField()
    population_size = models.IntegerField()
    notes           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ["-best_fitness", "-created_at"]
        verbose_name = "Run génétique"

    def __str__(self):
        return f"Gen {self.generation} — fitness={self.best_fitness:.4f}"
