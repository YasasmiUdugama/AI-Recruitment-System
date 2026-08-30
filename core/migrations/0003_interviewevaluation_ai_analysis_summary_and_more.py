

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_interviewresponse_video_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='interviewevaluation',
            name='ai_analysis_summary',
            field=models.TextField(blank=True, default='', help_text='Human-readable summary of AI analysis'),
        ),
        migrations.AddField(
            model_name='interviewevaluation',
            name='emotion_score_avg',
            field=models.FloatField(default=0.0, help_text='Average emotion score across all responses'),
        ),
        migrations.AddField(
            model_name='interviewevaluation',
            name='integrity_score_avg',
            field=models.FloatField(default=0.0, help_text='Average integrity/proctoring score across all responses'),
        ),
        migrations.AddField(
            model_name='interviewevaluation',
            name='total_violations',
            field=models.IntegerField(default=0, help_text='Total proctoring violations across all responses'),
        ),
        migrations.AddField(
            model_name='interviewevaluation',
            name='voice_confidence_avg',
            field=models.FloatField(default=0.0, help_text='Average voice confidence across all responses'),
        ),
        migrations.AddField(
            model_name='interviewresponse',
            name='proctoring_data',
            field=models.JSONField(blank=True, default=dict, help_text='Object detection & head pose proctoring results'),
        ),
        migrations.AlterField(
            model_name='interviewevaluation',
            name='recommendation',
            field=models.CharField(choices=[('strong_hire', 'Strong Hire'), ('hire', 'Hire'), ('consider', 'Consider'), ('not_recommended', 'Not Recommended'), ('review_required', 'Review Required'), ('rejected', 'Rejected')], default='not_recommended', max_length=20),
        ),
        migrations.AlterField(
            model_name='interviewresponse',
            name='emotion_data',
            field=models.JSONField(blank=True, default=dict, help_text='DeepFace emotion analysis results'),
        ),
        migrations.AlterField(
            model_name='interviewresponse',
            name='voice_analysis',
            field=models.JSONField(blank=True, default=dict, help_text='Whisper + Librosa voice analysis results'),
        ),
    ]
