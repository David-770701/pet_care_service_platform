from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pet_core', '0010_vaccine_series_fields'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='vaccine',
            new_name='pet_core_va_series__d15150_idx',
            old_name='pet_core_va_series__3e09a1_idx',
        ),
    ]
