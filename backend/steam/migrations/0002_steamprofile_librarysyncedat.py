from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('steam', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='steamprofile',
            name='librarySyncedAt',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
