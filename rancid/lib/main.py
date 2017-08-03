import subprocess
from base64 import b64encode,b64decode
import os
import shutil
from rancid.lib.fileops import RouterDB,Cloginrc,RancidConf
from rancid.models import Device,RancidGroupSetting,RancidGroupPermission
from django.conf import settings

rcFile = RancidConf()
crcFile = Cloginrc()

rancid_CVSROOT = rcFile.readSetting("CVSROOT").replace("$BASEDIR",settings.RANCID_ROOT)
rancid_LOGDIR = rcFile.readSetting("LOGDIR").replace("$BASEDIR",settings.RANCID_ROOT)

def get_permitted_groups(user):
    if user.is_staff:
        permitted_groups = rcFile.readSetting("LIST_OF_GROUPS").split(" ")
    else:
        groups = user.groups.all()
        group_permissions = RancidGroupPermission.objects.filter(djangoGroup__in=groups)
        permitted_groups = list(set([gp.rancidGroup for gp in group_permissions]))
    return(permitted_groups)


class DjancidBase(object):
    '''Inheritable class for Djancid classes'''
    def __str__(self):
        return(self.name)

    def getSetting(self,settingName):
        '''Get specific setting from details dictionaries stored in object'''
        if settingName not in settings.ALLSETTINGS:
            raise(BadSettingName("{sn} is not a valid setting name. Valid names are {vn}".format(sn=settingName,vn=settings.ALLSETTINGS)))
        for detail in [self.dbDetails,self.rcDetails,self.exDetails]:
            if settingName in detail.keys():
                settingValue = detail[settingName]
        return(settingValue)

    def putSetting(self,settingName,settingValue):
        '''Add a specific setting to details dictionaries stored in object'''
        if settingName in settings.DBSETTINGS:
            self.dbDetails[settingName] = settingValue
        elif settingName in settings.RCSETTINGS:
            self.rcDetails[settingName] = settingValue
        elif settingName in settings.EXTRASETTINGS:
            self.exDetails[settingName] = settingValue
        else:
            raise(BadSettingName("settingName {sn} is invalid. Must be one of: {asl}".format(sn=settingName,asl=settings.ALLSETTINGS)))
        self.fillAllSettings()

    def fillAllSettings(self):
        for details in [self.dbDetails,self.rcDetails,self.exDetails]:
            for k,v in details.items():
                self.allSettings[k] = v

    class BadSettingName(Exception):
        pass


class DjancidDevice(DjancidBase):
    '''Class to represent a Djancid Device. Device settings are pulled from:
    the group's router.db file, the .cloginrc file and the Django db'''

    def __init__(self,name,groupObj):
        self.name = name
        self.allSettings = {"name":self.name,"group":groupObj.name}
        self.parentGroup = groupObj
        self.rdbFile = RouterDB(self.parentGroup.name)
        self.b64code = self.ip_to_b64(self.name)
        self.crcFile = crcFile
        self.rcFile = rcFile
        self.exDetails = {}
        self.pullDetails()
        self.fillAllSettings()

    def ip_to_b64(self,ipStr):
        b64encoded = b64encode(bytes(ipStr,'ascii')).decode('ascii')
        return(b64encoded)

    def b64_to_ip(self,b64encoded):
        ipStr = b64decode(bytes(b64encoded,'ascii')).decode('ascii')
        return(ipStr)

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
        if "password" in self.rcDetails.keys():
            if isinstance(self.rcDetails['password'],list):
                self.exDetails['enablepassword'] = self.rcDetails['password'][1]
                self.rcDetails['password'] = self.rcDetails['password'][0]
        self.djangoDevice,created = Device.objects.get_or_create(ip=self.name)
        self.inherits = self.djangoDevice.inheritGroupSettings
        if self.inherits:
            self.inheritGroupSettings()
        self.fillAllSettings()

    def inheritGroupSettings(self):
        '''Pulls the settings defined in the parent group'''
        for settingName,settingValue in self.parentGroup.dbDetails.items():
            self.dbDetails[settingName] = settingValue
        for settingName,settingValue in self.parentGroup.rcDetails.items():
            self.rcDetails[settingName] = settingValue
        for settingName,settingValue in self.parentGroup.exDetails.items():
            self.exDetails[settingName] = settingValue

    def save(self):
        '''Add details and settings to router.db and cloginrc. Add inhertance setting to database'''
        if "deviceType" not in self.dbDetails.keys():
            raise(MissingRequiredSetting("deviceType setting needs to be defined"))
        if "status" not in self.dbDetails.keys():
            raise(MissingRequiredSetting("status setting needs to be defined"))
        self.djangoDevice,created = Device.objects.get_or_create(ip=self.name)
        self.djangoDevice.inheritGroupSettings = self.inherits
        self.djangoDevice.save()
        if self.inherits:
            self.inheritGroupSettings()
        try:
            self.rdbFile.addRouter(self.name,self.dbDetails['deviceType'],self.dbDetails['status'])
        except self.rdbFile.RouterAlreadyExistsException:
            self.rdbFile.editRouter(self.name,self.dbDetails['deviceType'],self.dbDetails['status'])
        for settingName,settingValue in self.rcDetails.items():
            self.crcFile.addDetail(self.name,settingName,settingValue)
        if self.exDetails:
            if "enablepassword" in self.exDetails.keys():
                passwordValue = [self.rcDetails['password'],self.exDetails['enablepassword']]
                self.crcFile.addDetail(self.name,"password",passwordValue)

    def delete(self):
        '''Remove from routerdb and cloginrc and django database'''
        self.rdbFile.deleteRouter(self.name)
        self.crcFile.deleteRouterDetails(self.name)
        self.djangoDevice.delete()

    def fillAllSettings(self):
        '''Creates an allSettings dict attr that has all relevant settings.
        This is used for passing to forms etc'''
        for details in [self.dbDetails,self.rcDetails,self.exDetails]:
            for k,v in details.items():
                self.allSettings[k] = v
        self.allSettings['inherits'] = self.inherits
        self.allSettings['group'] = self.parentGroup.name
        self.allSettings['name'] = self.name

    def deleteSetting(self,settingName):
        if settingName in self.rcDetails.keys():
            del self.rcDetails[settingName]
            self.crcFile.deleteDetail(self.name,settingName)
        if settingName in self.exDetails.keys():
            del self.exDetails[settingName]


class DjancidGroup(DjancidBase):
    '''Class to represent a Djancid Group. Settings pulled from Django db, devices pulled from 
    router.db file in the group's rancid directory'''
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
        self.exDetails = {}
        self.pullSettings()
        if self.rdbFile is not None:
            self.devices = self.rdbFile.getAllRouters()
        else:
            self.devices = []
        self.fillAllSettings()

    def pullSettings(self):
        '''Pull all settings objects from Django database'''
        self.groupSettings = RancidGroupSetting.objects.filter(rancidGroup=self.name)
        for setting in self.groupSettings:
            if setting.settingName in settings.DBSETTINGS:
                self.dbDetails[setting.settingName] = setting.settingValue
            elif setting.settingName in settings.RCSETTINGS:
                self.rcDetails[setting.settingName] = setting.settingValue
            elif setting.settingName in settings.EXTRASETTINGS:
                self.exDetails[setting.settingName] = setting.settingValue

    def save(self):
        '''Write group to LIST_OF_GROUPS if not exist. Save settings to database'''
        groups = self.rcFile.readSetting("LIST_OF_GROUPS")
        if self.name not in groups.split(" "):
            self.rcFile.appendValue("LIST_OF_GROUPS",self.name)
            subprocess.call(os.path.join(settings.RANCID_BIN_DIR,"rancid-cvs"))
        for detail in [self.dbDetails,self.rcDetails,self.exDetails]:
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

    def deleteSetting(self,settingName):
        groupSetting = RancidGroupSetting.objects.filter(rancidGroup=self.name,settingName=settingName)
        if groupSetting.exists():
            groupSetting.delete()
        for detail in [self.dbDetails,self.rcDetails,self.exDetails]:
            if settingName in detail.keys():
                del detail[settingName]

    def addPermission(self,dangoGroup):
        rgp,created = RancidGroupPermission.objects.get_or_create(
                rancidGroup=self.name,djangoGroup=djangoGroup)
        if created:
            rgp.save()

    def deletePermission(self,djangoGroup):
        rgp = RancidGroupPermission.objects.filter(
                rancidGroup=self.name,djangoGroup=djangoGroup)
        if rgp.exists():
            rgp.delete()
