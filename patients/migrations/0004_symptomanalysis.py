from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0003_treatment_medication_alter_treatment_medication_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='SymptomAnalysis',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symptoms', models.TextField(help_text='Symptômes décrits par le patient')),
                ('suggested_diagnosis', models.TextField(blank=True)),
                ('urgency_level', models.CharField(
                    choices=[('low', 'Faible'), ('moderate', 'Modérée'),
                             ('high', 'Élevée'), ('emergency', 'Urgence')],
                    default='low', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('patient', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='symptom_analyses',
                    to='patients.patient')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
