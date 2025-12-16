from django.db import models

# Create your models here.
class Drill(models.Model):
    create_By = models.ForeignKey('account.User', on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    category = models.TextField(max_length=100)
    description = models.TextField(max_length=250)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name