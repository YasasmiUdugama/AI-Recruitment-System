
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_remove_interviewevaluation_ai_analysis_summary_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='interview',
            name='questions_json',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
