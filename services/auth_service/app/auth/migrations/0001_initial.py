from django.db import migrations, models
from django.utils import timezone
from datetime import timedelta
import django.db.models.deletion
import uuid
import app.auth.models


def _expira_at_default():
    return timezone.now() + timedelta(minutes=10)


def _expira_rt_default():
    return timezone.now() + timedelta(days=7)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="Usuario",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4,
                 editable=False, primary_key=True)),
                ("password", models.CharField(
                    max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(
                    blank=True, null=True, verbose_name="last login")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("nombre", models.CharField(max_length=150)),
                ("rol", models.CharField(
                    choices=[
                        ("admin_central", "Admin Central"),
                        ("gerente_local", "Gerente Local"),
                        ("supervisor", "Supervisor"),
                        ("cocinero", "Cocinero"),
                        ("mesero", "Mesero"),
                        ("cajero", "Cajero"),
                        ("repartidor", "Repartidor"),
                    ],
                    default="mesero", max_length=20,
                )),
                ("restaurante_id", models.UUIDField(blank=True, null=True)),
                ("empleado_id", models.UUIDField(blank=True, null=True)),
                ("activo", models.BooleanField(default=True)),
                ("email_verificado", models.BooleanField(default=False)),
                ("is_staff", models.BooleanField(default=False)),
                ("is_superuser", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("groups", models.ManyToManyField(
                    blank=True,
                    help_text="The groups this user belongs to.",
                    related_name="auth_app_usuario_set",
                    to="auth.group",
                    verbose_name="groups",
                )),
                ("user_permissions", models.ManyToManyField(
                    blank=True,
                    help_text="Specific permissions for this user.",
                    related_name="auth_app_usuario_set",
                    to="auth.permission",
                    verbose_name="user permissions",
                )),
            ],
            options={
                "verbose_name": "Usuario",
                "verbose_name_plural": "Usuarios",
                "app_label": "auth_app",
            },
        ),
        migrations.CreateModel(
            name="RefreshToken",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4,
                 editable=False, primary_key=True)),
                ("token", models.TextField(unique=True)),
                ("revocado", models.BooleanField(default=False)),
                ("creado_at", models.DateTimeField(auto_now_add=True)),
                ("expira_at", models.DateTimeField(default=_expira_rt_default)),
                ("usuario", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="refresh_tokens",
                    to="auth_app.usuario",
                )),
            ],
            options={"verbose_name": "Refresh Token", "app_label": "auth_app"},
        ),
        migrations.CreateModel(
            name="EmailVerificationCode",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4,
                 editable=False, primary_key=True)),
                ("codigo", models.CharField(max_length=6,
                 default=app.auth.models._generar_codigo)),
                ("intentos", models.PositiveSmallIntegerField(default=0)),
                ("creado_at", models.DateTimeField(auto_now_add=True)),
                ("expira_at", models.DateTimeField(default=_expira_at_default)),
                ("usuario", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="verification_codes",
                    to="auth_app.usuario",
                )),
            ],
            options={
                "verbose_name": "Código de verificación de email",
                "app_label": "auth_app",
            },
        ),
        migrations.AddIndex(
            model_name="refreshtoken",
            index=models.Index(fields=["token"], name="auth_app_re_token_idx"),
        ),
    ]
