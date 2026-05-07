from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('consultations', '0001_initial'),
        ('patients', '0006_externalpatient_patientlinkrequest'),
    ]

    operations = [
        # Rendre patient nullable (pour supporter les patients sans compte)
        migrations.AlterField(
            model_name='consultation',
            name='patient',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='consultations_as_patient',
                to='patients.patient',
            ),
        ),
        # Ajouter external_patient FK
        migrations.AddField(
            model_name='consultation',
            name='external_patient',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='consultations',
                to='patients.externalpatient',
            ),
        ),
    ]
