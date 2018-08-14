
"""
    contains the models
"""
from django.db import models
from django.utils import timezone


class Camera(models.Model):

    ID = models.IntegerField(unique=True, db_column='ID')
    url = models.CharField(max_length=100)


class Stream(models.Model):

    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    startTime = models.DateTimeField()
    # endTime = models.DateTimeField()
    video_path = models.CharField(max_length=1000,default='unknown')
