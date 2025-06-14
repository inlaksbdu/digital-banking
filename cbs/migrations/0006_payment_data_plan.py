# Generated by Django 5.2.1 on 2025-06-07 04:50

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cbs", "0005_paymentbiller_payment"),
        ("datatable", "0004_telcodataplan"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="data_plan",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="payments",
                to="datatable.telcodataplan",
            ),
        ),
    ]
