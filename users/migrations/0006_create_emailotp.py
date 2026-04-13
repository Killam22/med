"""
Migration 0006 : Crée la table users_emailotp (EmailOTP model).
Ce modèle a été ajouté lors du refactoring OTP mais n'avait pas de migration.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_fix_legacy_columns'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailOTP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('otp', models.CharField(max_length=6)),
                ('purpose', models.CharField(
                    choices=[('register', 'Registration'), ('reset', 'Password Reset')],
                    max_length=16,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_used', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
