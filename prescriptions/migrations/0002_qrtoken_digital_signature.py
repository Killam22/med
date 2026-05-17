from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prescriptions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='qrtoken',
            name='digital_signature',
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
