from django.db import models

class Society(models.Model):
    society_name = models.CharField(max_length=100)
    owner_name = models.CharField(max_length=100)
    incharge = models.CharField(max_length=100)
    address = models.TextField()
    
class Flat(models.Model):
    flat_number = models.CharField(max_length=20)
    owner_name = models.CharField(max_length=100)
    floor = models.IntegerField()
    society_name = models.CharField(max_length=100)

    def __str__(self):
        return self.flat_number    
