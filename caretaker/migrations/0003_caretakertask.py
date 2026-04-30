from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('caretaker', '0002_remove_caretaker_professional_license_number_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CaretakerTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=300)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(
                    choices=[('pending', 'En attente'), ('done', 'Effectuée'), ('cancelled', 'Annulée')],
                    default='pending',
                    max_length=20,
                )),
                ('due_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('care_request', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tasks',
                    to='caretaker.carerequest',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
