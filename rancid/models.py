from django.db import models
from django.contrib.auth.models import Group

class RancidGroupPermission(models.Model):
    rancidGroup = models.CharField(max_length=100)
    djangoGroup = models.ForeignKey(Group)    

class Device(models.Model):
    ip = models.CharField(max_length=100)
    inheritGroupSettings = models.BooleanField(default=True)

class RancidGroupSetting(models.Model):
    rancidGroup = models.CharField(max_length=100)
    settingName = models.CharField(max_length=20)
    settingValue = models.CharField(max_length=100)
