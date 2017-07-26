import subprocess
import os
import shutil
from rancid.lib.fileops import RouterDB,Cloginrc,RancidConf
from rancid.models import Device,RancidGroupSetting
from django.conf import settings

rcFile = RancidConf()
crcFile = Cloginrc()

rancid_CVSROOT = rcFile.readSetting("CVSROOT").replace("$BASEDIR",settings.RANCID_ROOT)
rancid_LOGDIR = rcFile.readSetting("LOGDIR").replace("$BASEDIR",settings.RANCID_ROOT)

def get_permitted_groups(user):
    if user.is_staff:
        permitted_groups = rcFile.readSetting("LIST_OF_GROUPS").split(" ")
    else:
        groups = user.groups
        group_permissions = RancidGroupPermission.objects.filter(djangoGroup__in=groups)
        permitted_groups = list(set([gp.rancidGroup for gp in group_permissions]))
    return(permitted_groups)


class DjancidBase(object):
    def __str__(self):
        return(self.name)
    def getSetting(self,settingName):
        '''Get specific setting from details dictionaries stored in object'''
        if settingName not in settings.ALLSETTINGS:
            raise(BadSettingName("{sn} is not a valid setting name. Valid names are {vn}".format(sn=settingName,vn=settings.ALLSETTINGS)))
        for detail in [dbDetails,rcDetails]:
            if settingName in detail.keys():
                settingValue = detail[settingName]
        return(settingValue)
    def putSetting(self,settingName,settingValue):
        '''Add a specific setting to details dictionaries stored in object'''
        if settingName in settings.DBSETTINGS:
            self.dbDetails[settingName] = settingValue
        elif settingName in settings.RCSETTINGS:
            self.rcDetails[settingName] = settingValue
        else:
            raise(BadSettingName("settingName {sn} is invalid. Must be one of: {asl}".format(sn=settingName,asl=settings.ALLSETTINGS)))
        self.fillAllSettings()
    def fillAllSettings(self):
        for details in [self.dbDetails,self.rcDetails]:
            for k,v in details.items():
                self.allSettings[k] = v
    class BadSettingName(Exception):
        pass

class DjancidDevice(DjancidBase):
    def __init__(self,name,groupObj):
        self.name = name
        self.allSettings = {"name":self.name,"group":groupObj.name}
        self.parentGroup = groupObj
        self.rdbFile = RouterDB(self.parentGroup.name)
        self.crcFile = crcFile
        self.rcFile = rcFile
        self.pullDetails()
        if self.inherits:
            self.inheritGroupSettings()
    def pullDetails(self):
        '''Gets the details for this device from files and database'''
        try:
            self.dbDetails = self.rdbFile.getRouterDetails(self.name)
        except self.rdbFile.RouterNotFoundException:
            self.dbDetails = {}
        try:
            self.rcDetails = self.crcFile.getRouterDetails(self.name)
        except self.crcFile.NoRouterDetails:
            self.rcDetails = {}
        self.djangoDevice,created = Device.objects.get_or_create(ip=self.name)
        self.inherits = self.djangoDevice.inheritGroupSettings
        self.fillAllSettings()
    def inheritGroupSettings(self):
        '''Pulls the settings defined in the parent group'''
        for settingName,settingValue in self.parentGroup.dbDetails.items():
            self.dbDetails[settingName] = settingValue
        for settingName,settingValue in self.parentGroup.rcDetails.items():
            self.rcDetails[settingName] = settingValue
        self.fillAllSettings()
    def save(self):
        '''Add details and settings to router.db and cloginrc. Add inhertance setting to database'''
        if "deviceType" not in self.dbDetails.keys():
            raise(MissingRequiredSetting("deviceType setting needs to be defined"))
        if "status" not in self.dbDetails.keys():
            raise(MissingRequiredSetting("status setting needs to be defined"))
        try:
            self.rdbFile.addRouter(self.name,self.dbDetails['deviceType'],self.dbDetails['status'])
        except self.rdbFile.RouterAlreadyExistsException:
            self.rdbFile.editRouter(self.name,self.dbDetails['deviceType'],self.dbDetails['status'])
        self.djangoDevice,created = Device.objects.get_or_create(ip=self.name)
        self.djangoDevice.inheritGroupSettings = self.inherits
        self.djangoDevice.save()
        for settingName,settingValue in self.rcDetails.items():
            self.crcFile.addDetail(self.name,settingName,settingValue)
    def delete(self):
        '''Remove from routerdb and cloginrc and django database'''
        self.rdbFile.deleteRouter(self.name)
        self.crcFile.deleteRouterDetails(self.name)
        self.djangoDevice.delete()
    def fillAllSettings(self):
        for details in [self.dbDetails,self.rcDetails]:
            for k,v in details.items():
                self.allSettings[k] = v
        self.allSettings['inherits'] = self.inherits
        self.allSettings['group'] = self.parentGroup.name
        self.allSettings['name'] = self.name

class DjancidGroup(DjancidBase):
    def __init__(self,name):
        self.name = name.upper()
        self.allSettings = {"name":self.name}
        try:
            self.rdbFile = RouterDB(self.name)
        except FileNotFoundError:
            self.rdbFile = None
        self.crcFile = crcFile
        self.rcFile = rcFile
        self.dbDetails = {}
        self.rcDetails = {}
        self.pullSettings()
        if self.rdbFile is not None:
            self.devices = self.rdbFile.getAllRouters()
        else:
            self.devices = []
        self.fillAllSettings()
    def pullSettings(self):
        '''Pull all settings objects from Django database'''
        self.groupSettings = RancidGroupSetting.objects.filter(rancidGroup=self.name)
        if self.groupSettings:
            for setting in self.groupSettings:
                if setting.settingName in ["deviceType","status"]:
                    self.dbDetails[setting.settingName] = setting.settingValue
                else:
                    self.rcDetails[setting.settingName] = setting.settingValue
        self.fillAllSettings()
    def save(self):
        '''Write group to LIST_OF_GROUPS if not exist. Save settings to database'''
        groups = self.rcFile.readSetting("LIST_OF_GROUPS")
        if self.name not in groups.split(" "):
            self.rcFile.appendValue("LIST_OF_GROUPS",self.name)
            subprocess.call(os.path.join(settings.RANCID_BIN_DIR,"rancid-cvs"))
        for detail in [self.dbDetails,self.rcDetails]:
            for settingName,settingValue in detail.items():
                settingObj, created = RancidGroupSetting.objects.get_or_create(rancidGroup=self.name,settingName=settingName)
                settingObj.settingValue = settingValue
                settingObj.save()
        self.groupSettings = RancidGroupSetting.objects.filter(rancidGroup=self.name)
        self.refreshDevices()
    def delete(self):
        '''Delete from LIST_OF_GROUPS if exists. Delete settings from database'''
        groups = self.rcFile.readSetting("LIST_OF_GROUPS")
        if self.name in groups.split(" "):
            self.rcFile.deleteValue("LIST_OF_GROUPS",self.name)
            subprocess.call(os.path.join(settings.RANCID_BIN_DIR,"rancid-cvs"))
        self.groupSettings = RancidGroupSetting.objects.filter(rancidGroup=self.name)
        self.groupSettings.delete()
        self.deleteDevices()
        deleteDirs = [os.path.join(settings.RANCID_ROOT,self.name),os.path.join(rancid_CVSROOT,self.name)]
        for path in deleteDirs:
            if os.path.exists(path):
                shutil.rmtree(path)
        deleteLogs = [f for f in os.listdir(rancid_LOGDIR) if self.name in f]
        for logFile in deleteLogs:
            path = os.path.join(rancid_LOGDIR,logFile)
            os.remove(path)
    def deleteDevices(self):
        if self.rdbFile is not None:
            self.devices = self.rdbFile.getAllRouters()
        for device in self.devices:
            djDevice = DjangoDevice(device['ip'])
            djDevice.delete()
        self.devices = []
    def refreshDevices(self):
        if self.rdbFile is not None:
            self.devices = self.rdbFile.getAllRouters()
        for device in self.devices:
            djDevice = DjancidDevice(device['ip'],self)
            if djDevice.inherits:
                djDevice.save()
