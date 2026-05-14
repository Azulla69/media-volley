from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MatchSet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('set_number', models.IntegerField(verbose_name='Номер партии')),
                ('score_home', models.IntegerField(verbose_name='Очки хозяев')),
                ('score_away', models.IntegerField(verbose_name='Очки гостей')),
                ('match', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sets', to='matches.match', verbose_name='Матч')),
            ],
            options={
                'verbose_name': 'Партия',
                'verbose_name_plural': 'Партии',
                'ordering': ['set_number'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='matchset',
            unique_together={('match', 'set_number')},
        ),
        migrations.AlterField(
            model_name='match',
            name='score_home',
            field=models.IntegerField(blank=True, null=True, verbose_name='Партии хозяев'),
        ),
        migrations.AlterField(
            model_name='match',
            name='score_away',
            field=models.IntegerField(blank=True, null=True, verbose_name='Партии гостей'),
        ),
    ]
