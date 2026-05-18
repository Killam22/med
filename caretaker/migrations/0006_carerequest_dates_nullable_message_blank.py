from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('caretaker', '0005_medication_schedule'),
    ]

    operations = [
        migrations.AlterField(
            model_name='carerequest',
            name='start_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='carerequest',
            name='patient_message',
            field=models.TextField(blank=True, help_text='Détails des tâches et besoins médicaux'),
        ),
    ]
