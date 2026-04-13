"""
Migration 0005 : Neutralise les colonnes héritées de l'ancien modèle
qui ne sont plus dans CustomUser mais existent en DB avec une contrainte NOT NULL.
Rend blood_type, emergency_contact, access_level optionnels (blank=True, default='').
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_add_missing_fields'),
    ]

    operations = [
        # blood_type : existait dans l'ancien modèle, plus dans le nouveau,
        # mais toujours en DB avec NOT NULL → on le rend nullable pour ne pas bloquer les INSERT
        migrations.AlterField(
            model_name='customuser',
            name='blood_type',
            field=models.CharField(blank=True, default='', max_length=5),
        ),
        # emergency_contact : même raison
        migrations.AlterField(
            model_name='customuser',
            name='emergency_contact',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        # access_level : même raison
        migrations.AlterField(
            model_name='customuser',
            name='access_level',
            field=models.IntegerField(blank=True, default=1),
        ),
        # address : CharField dans le nouveau modèle, TextField dans l'ancien
        migrations.AlterField(
            model_name='customuser',
            name='address',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
