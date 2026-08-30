
import core.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_interview_questions_json'),
    ]

    operations = [
        migrations.AddField(
            model_name='interview',
            name='full_recording',
            field=models.FileField(blank=True, null=True, upload_to=core.models.interview_video_path),
        ),
    ]
