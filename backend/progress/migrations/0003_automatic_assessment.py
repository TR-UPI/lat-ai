from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('progress', '0002_exerciseattempt')]
    operations = [
        migrations.AddField(model_name='exerciseattempt', name='assessment', field=models.JSONField(blank=True, default=dict, editable=False)),
        migrations.AlterField(model_name='exerciseattempt', name='status', field=models.CharField(choices=[('submitted','Отправлено'),('checked','Проверено'),('auto_checked','Проверено ИИ'),('assessment_failed','Автопроверка не завершена')],default='submitted',max_length=20,verbose_name='Статус проверки')),
    ]
