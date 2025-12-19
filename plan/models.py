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
    


class Block(models.Model):
    assign_team = models.ForeignKey('account.TeamMember', on_delete=models.CASCADE)
    drill = models.ForeignKey(Drill, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    start_time  = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):  
        return f"{self.drill.name} - {self.title}"
    

class plan(models.Model):
    plan_title = models.CharField(max_length=100)
    Drill = models.ForeignKey(Drill, on_delete=models.CASCADE)
    prectice_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.Drill.name} - {self.prectice_time}"