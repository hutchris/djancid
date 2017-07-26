import os
from base64 import b64encode,b64decode
from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from rancid.lib.main import DjancidGroup,DjancidDevice,get_permitted_groups
from rancid.lib.fileops import RancidConf,Cloginrc,RouterDB
from rancid.models import RancidGroupPermission
from rancid.forms import GroupForm,DeviceForm

rcFile = RancidConf()

class BaseView(LoginRequiredMixin,View):
    def get_permitted_groups(self,user):
        if user.is_staff:
            permitted_groups = rcFile.readSetting("LIST_OF_GROUPS").split(" ")
        else:
            groups = user.groups
            group_permissions = RancidGroupPermission.objects.filter(djangoGroup__in=groups)
            permitted_groups = list(set([gp.rancidGroup for gp in group_permissions]))
        return(permitted_groups)

    def ip_to_b64(self,ipStr):
        b64encoded = b64encode(bytes(ipStr,'ascii')).decode('ascii')
        return(b64encoded)

    def b64_to_ip(self,b64encoded):
        ipStr = b64decode(bytes(b64encoded,'ascii')).decode('ascii')
        return(ipStr)


class NewGroup(BaseView):
    def get(self,request):
        if request.user.is_staff:
            form = GroupForm()
            context = {'form':form}
            return(render(request,'rancid/NewGroup.html',context))
        else:
            return(redirect("/"))

    def post(self,request):
        form = GroupForm(request.POST)
        if form.is_valid():
            groupObj = DjancidGroup(form.cleaned_data['name'])
            for settingName,settingValue in form.cleaned_data.items():
                if settingName in settings.ALLSETTINGS and settingValue not in ['------','',None]:
                    groupObj.putSetting(settingName,settingValue)
                elif settingName.startswith("perm_"):
                    if settingValue:
                        rgp,created = RancidGroupPermission.objects.get_or_create(
                                rancidGroup=groupObj.name,
                                djangoGroup=settingName.replace("perm_","")
                            )
                        if created:
                            rgp.save()
            groupObj.save()
        else:
            return(HttpResponse(form.errors))
        return(redirect("GroupDetails",group=groupObj.name))


class GroupDetails(NewGroup):
    def get(self,request,group):
        permitted_groups = get_permitted_groups(request.user)
        if group in permitted_groups:
            context = {}
            djGroup = DjancidGroup(group)
            djGroup.djDevices = [DjancidDevice(d) for d in djGroup.devices]
            context["group"] = djGroup
            context["form"] = GroupForm(djGroup.allSettings)
            return(render(request,'rancid/GroupDetails.html',context))
        else:
            return(redirect("/"))


class NewDevice(BaseView):
    def get(self,request,group):
        permitted_groups = get_permitted_groups(request.user)
        if group in permitted_groups:
            groupObj = DjancidGroup(group)
            deviceObj = DjancidDevice("",groupObj)
            settingsDict = dict(deviceObj.allSettings)
            del settingsDict['name']
            settingsDict["inherits"] = True
            form = DeviceForm(request.user,settingsDict)
            context = {"form":form}
            context['group'] = groupObj
            return(render(request,'rancid/NewDevice.html',context))
        else:
            return(redirect(str(1/0)))

    def post(self,request,group):
        form = DeviceForm(request.user,request.POST)
        permitted_groups = get_permitted_groups(request.user)
        if form.is_valid() and group in permitted_groups:
            groupObj = DjancidGroup(group)
            deviceObj = DjancidDevice(form.cleaned_data['ip'],groupObj)
            for settingName,settingValue in form.cleaned_data.items():
                if settingName in settings.ALLSETTINGS and settingValue not in ['------','',None]:
                    deviceObj.putSetting(settingName,settingValue)
                if settingName == "inherits":
                    deviceObj.inherits = settingValue
            deviceObj.save()
            return(redirect("DeviceDetails",group=groupObj.name,device=self.ip_to_b64(deviceObj.name)))
        else:
            return(HttpResponse(str(form.errors)))


class DeviceDetails(BaseView):
    def get(self,request,group,device):
        device = self.b64_to_ip(device)
        permitted_groups = get_permitted_groups(request.user)
        if group in permitted_groups:
            groupObj = DjancidGroup(group)
            deviceObj = DjancidDevice(device,groupObj)
            deviceObj.b64code = self.ip_to_b64(deviceObj.name)
            context = {"device":deviceObj,"group":groupObj}
            form = DeviceForm(request.user,deviceObj.allSettings)
            if deviceObj.inherits:
                for fieldName,fieldValue in form.fields.items():
                    if fieldName in groupObj.allSettings.keys():
                        fieldValue.disabled = True
            context['form'] = form
            return(render(request,'rancid/DeviceDetails.html',context))
        else:
            return(redirect("/"))
