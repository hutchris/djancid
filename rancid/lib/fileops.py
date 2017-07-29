from django.conf import settings
import os

def get_device_types():
    filePath = os.path.join(settings.RANCID_SETTINGS_DIR,'rancid.types.base')
    with open(filePath,"r") as f:
        lines = f.readlines()
    typesRaw = [line.split(";")[0] for line in lines if ";" in line and "#" not in line]
    types = list(set(typesRaw))
    types.sort()
    return(types)


class RancidConf(object):
    def __init__(self,confDir=settings.RANCID_SETTINGS_DIR):
        self.confDir = os.path.join(confDir,"rancid.conf")
    def readSetting(self,setting):
        '''Read a setting from the config file'''
        with open(self.confDir,"r") as confFile:
            lines = confFile.readlines()
        try:
            settingLine = [line for line in lines if line.startswith(setting)][0]
        except IndexError:
            raise(self.SettingNotExistException("Setting {s} does not exist".format(s=setting)))
        output = settingLine.split(";")[0].split("=")[1].replace('"',"")
        return(output)
    def writeSetting(self,setting,value):
        '''Completely replace a setting value with the supplied value'''
        with open(self.confDir,"r") as confFile:
            lines = confFile.readlines()
        try:
            settingLine = [line for line in lines if line.startswith(setting)][0]
        except IndexError:
            raise(self.SettingNotExistException("Setting {s} does not exist".format(s=setting)))
        oldSetting = settingLine.split(";")[0].split("=")[1].replace('"',"")
        for i,line in enumerate(lines):
            if line == settingLine:
                lines[i] = settingLine.replace(oldSetting,value)
        with open(self.confDir,"w") as confFile:
            confFile.writelines(lines)
    def appendValue(self,setting,value,seperator=" "):
        '''Append a value to the list of existing values for a setting'''
        with open(self.confDir,"r") as confFile:
            lines = confFile.readlines()
        try:
            settingLine = [line for line in lines if line.startswith(setting)][0]
        except IndexError:
            raise(self.SettingNotExistException("Setting {s} does not exist".format(s=setting)))
        oldValues = settingLine.split(";")[0].split("=")[1].replace('"',"")
        newValues = "{ov}{sp}{v}".format(ov=oldValues,sp=seperator,v=value)
        for i,line in enumerate(lines):
            if line == settingLine:
                lines[i] = settingLine.replace(oldValues,newValues)
        with open(self.confDir,"w") as confFile:
            confFile.writelines(lines)
    def deleteValue(self,setting,value,seperator=" "):
        '''Remove a single value from a list of values for a setting'''
        with open(self.confDir,"r") as confFile:
            lines = confFile.readlines()
        try:
            settingLine = [line for line in lines if line.startswith(setting)][0]
        except IndexError:
            raise(self.SettingNotExistException("Setting {s} does not exist".format(s=setting)))
        oldValues = settingLine.split(";")[0].split("=")[1].replace('"',"")
        oldValuesList = oldValues.split(seperator)
        try:
            oldValuesList.remove(value)
        except ValueError:
            raise(self.ValueNotExistException("{v} is not in list of values for setting {s}".format(v=value,s=setting)))
        newValues = seperator.join(oldValuesList)
        for i,line in enumerate(lines):
            if line == settingLine:
                lines[i] = settingLine.replace(oldValues,newValues)
        with open(self.confDir,"w") as confFile:
            confFile.writelines(lines)
    class SettingNotExistException(Exception):
        pass
    class ValueNotExistException(Exception):
        pass

class RouterDB(object):
    def __init__(self,groupName,rancidRoot=settings.RANCID_ROOT):
        self.routerDBDir = os.path.join(rancidRoot,groupName,"router.db")
        if not os.path.exists(self.routerDBDir):
            raise(FileNotFoundError("File {f} does not exist".format(f=self.routerDBDir)))
    def addRouter(self,ip,deviceType="cisco",status="up"):
        if isinstance(status,bool):
            if status:
                status = "up"
            else:
                status = "down"
        with open(self.routerDBDir,"r") as routerDBFile:
            lines = routerDBFile.readlines()
        for line in lines:
            if line.startswith(ip):
                raise(self.RouterAlreadyExistsException("Router {r} already exists".format(r=ip)))
        lines.append("{ip};{dt};{st}\n".format(ip=ip,dt=deviceType,st=status))
        with open(self.routerDBDir,"w") as routerDBFile:
            routerDBFile.writelines(lines) 
    def deleteRouter(self,ip):
        with open(self.routerDBDir,"r") as routerDBFile:
            lines = routerDBFile.readlines()
        lines = [line for line in lines if ip not in line]
        with open(self.routerDBDir,"w") as routerDBFile:
            routerDBFile.writelines(lines)
    def editRouter(self,ip,deviceType=None,status=None):
        with open(self.routerDBDir,"r") as routerDBFile:
            lines = routerDBFile.readlines()
        for i,line in enumerate(lines):
            if line.startswith(ip):
                routerLine = line.split(";")
                if deviceType is not None:
                    routerLine[1] = deviceType
                if status is not None:
                    if isinstance(status,bool):
                        if status:
                            status = "up"
                        else:
                            status = "down"
                    routerLine[2] = status
                lines[i] = "{l}\n".format(l=";".join(routerLine))
        with open(self.routerDBDir,"w") as routerDBFile:
            routerDBFile.writelines(lines)
    def getRouterDetails(self,ip):
        with open(self.routerDBDir,"r") as routerDBFile:
            lines = routerDBFile.readlines()
        routerLines = [line for line in lines if line.startswith(ip)]
        if routerLines:
            router = routerLines[0].replace("\n","").split(";")
        else:
            raise(self.RouterNotFoundException("Router does not exist: {r}".format(r=ip)))
        routerOutput = {"ip":ip,"deviceType":router[1],"status":router[2]}
        return(routerOutput)
    def getAllRouters(self):
        with open(self.routerDBDir,"r") as routerDBFile:
            lines = routerDBFile.readlines()
        routerLines = []
        for line in lines:
            router = line.replace("\n","").split(";")
            if len(router) == 3:
                routerLines.append({"ip":router[0],"deviceType":router[1],"status":router[2]})
        return(routerLines)
    class RouterAlreadyExistsException(Exception):
        pass
    class RouterNotFoundException(Exception):
        pass

class Cloginrc(object):
    def __init__(self,cloginrcDir=os.path.join(settings.RANCID_ROOT,".cloginrc")):
        self.cloginrcDir = cloginrcDir
    def getRouterDetails(self,ip):
        with open(self.cloginrcDir,"r") as cloginrcFile:
            lines = cloginrcFile.readlines()
        routerLines = [line for line in lines if ip in line]
        details = {}
        if routerLines:
            for line in routerLines:
                lineSplit = line.split(" ")
                if len(lineSplit) == 4:
                    value = lineSplit[3].replace("{","").replace("}","").replace("\n","")
                    if value in ["0","1"]:
                        value = bool(int(value))
                elif len(lineSplit) > 4:
                    value = []
                    for item in lineSplit[3:]:
                        item = item.replace("{","").replace("}","").replace("\n","")
                        if item in ["0","1"]:
                             item = bool(int(item))
                        value.append(item)
                details[lineSplit[1]] = value 
        else:
            raise(self.NoRouterDetails("No details configured for router: {ip}".format(ip=ip)))
        return(details)
    def addDetail(self,ip,name,value):
        if name not in settings.RCSETTINGS:
            raise(self.InvalidDetailName("{n} is not a valid cloginrc command".format(n=name)))
        with open(self.cloginrcDir,"r") as cloginrcFile:
            lines = cloginrcFile.readlines()
        if isinstance(value,bool):
            value = str(int(value))
        if isinstance(value,list):
            value = " ".join(["{{{v}}}".format(v=item) for item in value])
        else:
            value = "{{{v}}}".format(v=value)
        detailLine = "add {n} {ip} {v}\n".format(n=name,ip=ip,v=value)
        insertIndex = 0
        for i,line in enumerate(lines):
            if ip in line and name in line:
                lines.remove(line)
                insertIndex = i
                break
            elif ip in line:
                insertIndex = i
        lines.insert(insertIndex,detailLine)
        with open(self.cloginrcDir,"w") as cloginrcFile:
            cloginrcFile.writelines(lines)
    def addDetails(self,ip,detailsDict):
        for k,v in detailsDict.item():
            self.addDetail(ip=ip,name=k,value=v)
    def deleteDetail(self,ip,name):
        with open(self.cloginrcDir,"r"):
            lines = cloginrcDir.readlines()
        for line in lines:
            if ip in line and name in line:
                lines.remove(line)
        with open(self.cloginrcDir,"w") as cloginrcFile:
            cloginrcFile.writelines(lines)
    def deleteRouterDetails(self,ip):
        with open(self.cloginrcDir,"r") as cloginrcFile:
            lines = cloginrcFile.readlines()
        for line in lines:
            if ip in line:
                lines.remove(line)
        with open(self.cloginrcDir,"w") as cloginrcFile:
            cloginrcFile.writelines(lines)
    class InvalidDetailName(Exception):
        pass
    class NoRouterDetails(Exception):
        pass

