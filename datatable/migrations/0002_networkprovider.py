# Generated by Django 5.2.1 on 2025-06-07 01:05

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("datatable", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="NetworkProvider",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200, unique=True)),
                ("active", models.BooleanField(default=True)),
                ("uuid", models.UUIDField(blank=True, default=uuid.uuid4, null=True)),
                ("date_created", models.DateTimeField(auto_now_add=True)),
                ("last_udpated", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
