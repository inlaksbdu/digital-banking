# Generated by Django 5.2.1 on 2025-06-06 23:11

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cbs", "0002_alter_bankaccount_account_balance"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="bankaccount",
            options={"ordering": ("-default",)},
        ),
        migrations.AddField(
            model_name="bankaccount",
            name="default",
            field=models.BooleanField(default=False),
        ),
    ]
