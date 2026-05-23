from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminContactRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(
                    choices=[
                        ('technical', 'Problème technique'),
                        ('account', 'Compte / Accès'),
                        ('billing', 'Facturation'),
                        ('feature', 'Suggestion / Fonctionnalité'),
                        ('other', 'Autre'),
                    ],
                    default='other',
                    max_length=20,
                )),
                ('subject', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'En attente'),
                        ('in_progress', 'En cours'),
                        ('resolved', 'Traitée'),
                        ('rejected', 'Refusée'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('admin_response', models.TextField(blank=True, default='')),
                ('handled_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='admin_contact_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('handled_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='handled_contact_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
