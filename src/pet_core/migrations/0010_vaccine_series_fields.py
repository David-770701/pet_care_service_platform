from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pet_core', '0009_vaccinerecord_vaccine'),
    ]

    operations = [
        migrations.AddField(
            model_name='vaccine',
            name='dose_number',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='vaccine',
            name='full_name',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='vaccine',
            name='is_booster',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='vaccine',
            name='series_id',
            field=models.CharField(db_index=True, default='', max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='vaccine',
            name='total_basic_doses',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name='vaccine',
            name='duration_months',
            field=models.IntegerField(default=12),
        ),
        migrations.AddIndex(
            model_name='vaccine',
            index=models.Index(fields=['series_id', 'dose_number'], name='pet_core_va_series__3e09a1_idx'),
        ),
    ]
