"""
Migration 0004 : Aligne la DB avec le modèle CustomUser refactorisé.
Ajoute les colonnes vraiment manquantes après inspection de la DB réelle :
  - created_at (non présent en DB)
  - sex : max_length 1 → 10 (M/F → male/female)
  - first_name max_length 150 → 50
  - last_name  max_length 150 → 50
  - verification_status : nouveaux choix
  (photo, id_card_recto, id_card_verso déjà présents via migration 0003)
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_alter_customuser_id_card_recto_and_more'),
    ]

    operations = [
        # created_at — colonne manquante en DB
        migrations.AddField(
            model_name='customuser',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        # sex : max_length 1 → 10 pour supporter 'male' / 'female'
        migrations.AlterField(
            model_name='customuser',
            name='sex',
            field=models.CharField(
                blank=True,
                choices=[('male', 'Male'), ('female', 'Female')],
                max_length=10,
            ),
        ),
        # first_name : 150 → 50
        migrations.AlterField(
            model_name='customuser',
            name='first_name',
            field=models.CharField(blank=True, max_length=50),
        ),
        # last_name : 150 → 50
        migrations.AlterField(
            model_name='customuser',
            name='last_name',
            field=models.CharField(blank=True, max_length=50),
        ),
        # verification_status : nouveaux choices
        migrations.AlterField(
            model_name='customuser',
            name='verification_status',
            field=models.CharField(
                choices=[('pending', 'Pending'), ('verified', 'Verified'), ('rejected', 'Rejected')],
                default='pending',
                max_length=20,
            ),
        ),
    ]
