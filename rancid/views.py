import os
import logging
from base64 import b64encode,b64decode
from django.shortcuts import render,redirect
from django.http import HttpResponse,Http404
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django import forms
from rancid.lib.main import DjancidGroup,DjancidDevice,get_permitted_groups
from rancid.lib.fileops import RancidConf,Cloginrc,RouterDB
from rancid.lib.gitops import get_config,get_config_diffs
from rancid.models import RancidGroupPermission
from rancid.forms import GroupForm,DeviceForm

rcFile = RancidConf()

class BaseView(LoginRequiredMixin,View):
    def ip_to_b64(self,ipStr):
        b64encoded = b64encode(bytes(ipStr,'ascii')).decode('ascii')
        return(b64encoded)

    def b64_to_ip(self,b64encoded):
        ipStr = b64decode(bytes(b64encoded,'ascii')).decode('ascii')
        return(ipStr)


class AllDevices(BaseView):
    def get(self,request):
        permitted_groups = get_permitted_groups(request.user)
        context = {}
        groups = [DjancidGroup(gp) for gp in permitted_groups]
        for groupObj in groups:
            groupObj.djDevices = [DjancidDevice(dev['ip'],groupObj) for dev in groupObj.devices]
        context['groups'] = groups
        return(render(request,'rancid/AllDevices.html',context))


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
                if settingName in settings.ALLSETTINGS and settingValue not in ['------','',None,"00000000"]:
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


class GroupDetails(BaseView):
    def prepForm(self,groupObj,request=None):
        settingsDict = dict(groupObj.allSettings)
        for passwordSetting in ["password","enablepassword"]:
            if passwordSetting in settingsDict.keys():
                settingsDict[passwordSetting] = "00000000"
        if request is None:
            form = GroupForm(initial=settingsDict)
        else:
            form = GroupForm(request.POST,initial=settingsDict)
        form.fields['name'].widget = forms.HiddenInput()
        form.fields['name'].required = False
        return(form)

    def get(self,request,group):
        permitted_groups = get_permitted_groups(request.user)
        if group in permitted_groups:
            context = {}
            groupObj = DjancidGroup(group)
            groupObj.djDevices = [DjancidDevice(d['ip'],groupObj) for d in groupObj.devices]
            groupObj.fillAllSettings()
            form = self.prepForm(groupObj)
            context['form'] = form
            context['group'] = groupObj
            return(render(request,'rancid/GroupDetails.html',context))
        else:
            return(redirect("/"))

    def post(self,request,group):
        groupObj = DjancidGroup(group)
        form = self.prepForm(groupObj,request)
        permitted_groups = get_permitted_groups(request.user)
        if form.is_valid() and group in permitted_groups:
            for fieldName in form.changed_data:
                if fieldName in settings.ALLSETTINGS:
                    if form.cleaned_data[fieldName] in ['','------',None]:
                        groupObj.deleteSetting(fieldName)
                    else:
                        groupObj.putSetting(fieldName,form.cleaned_data[fieldName])
                elif fieldName.startswith("perm_"):
                    if form.cleaned_data[fieldName]:
                        groupObj.addPermission(fieldName.replace("perm_",""))
                    else:
                        groupObj.deletePermission(fieldName.replace("perm_",""))
            groupObj.save()
            context['form'] = form
            context['group'] = groupObj
            return(render(request,'rancid/GroupDetails.html',context))
        else:
            return(HttpResponse(form.errors))


class NewDevice(BaseView):
    def prepForm(self,deviceObj,request):
        deviceObj.fillAllSettings()
        settingsDict = dict(deviceObj.allSettings)
        for passwordSetting in ["password","enablepassword"]:
            if passwordSetting in settingsDict.keys():
                settingsDict[passwordSetting] = "00000000"
        if request.method == "POST":
            form = DeviceForm(request.user,request.POST,initial=settingsDict)
        else:
            del settingsDict['name']
            settingsDict['inherits'] = True
            form = DeviceForm(request.user,initial=settingsDict)
        return(form)
            
    def get(self,request,group):
        permitted_groups = get_permitted_groups(request.user)
        if group in permitted_groups:
            groupObj = DjancidGroup(group)
            deviceObj = DjancidDevice("",groupObj)
            form = self.prepForm(deviceObj,request)
            context = {"form":form}
            context['group'] = groupObj
            return(render(request,'rancid/NewDevice.html',context))
        else:
            return(redirect(str(1/0)))

    def post(self,request,group):
        permitted_groups = get_permitted_groups(request.user)
        if group in permitted_groups:
            tempForm = DeviceForm(request.user,request.POST)
            groupObj = DjancidGroup(group)
            deviceObj = DjancidDevice(tempForm['ip'].data,groupObj)
            form = self.prepForm(deviceObj,request)
            if form.is_valid():
                for fieldName in form.changed_data:
                    if fieldName in settings.ALLSETTINGS:
                        if form.cleaned_data[fieldName] in ['------','',None]:
                            deviceObj.deleteSetting(fieldName)
                        else:
                            deviceObj.putSetting(fieldName,form.cleaned_data[fieldName])
                    elif fieldName == "inherits":
                        deviceObj.inherits = settingValue
                deviceObj.save()
                return(redirect("DeviceDetails",group=groupObj.name,device=deviceObj.b64code))
            else:
                return(HttpResponse(str(form.errors)))
        else:
            raise(Http404("Permission Error"))


class DeviceDetails(NewDevice):
    def get(self,request,group,device):
        device = self.b64_to_ip(device)
        permitted_groups = get_permitted_groups(request.user)
        if group in permitted_groups:
            groupObj = DjancidGroup(group)
            deviceObj = DjancidDevice(device,groupObj)
            context = {"device":deviceObj,"group":groupObj}
            form = self.prepForm(deviceObj,request)
            form.fields['ip'].widget = forms.HiddenInput()
            form.fields['ip'].required = False
            if deviceObj.inherits:
                for fieldName,fieldValue in form.fields.items():
                    if fieldName in groupObj.allSettings.keys():
                        fieldValue.label = "{l} (i)".format(l=fieldValue.label)
            context['form'] = form
            return(render(request,'rancid/DeviceDetails.html',context))
        else:
            raise(Http404("Permission Error"))

    def post(self,request,group,device):
        context = {}
        groupObj = DjancidGroup(group)
        deviceObj = DjancidDevice(self.b64_to_ip(device),groupObj)
        form = self.prepForm(deviceObj,request)
        form.fields['ip'].widget = forms.HiddenInput()
        form.fields['ip'].required = False
        permitted_groups = get_permitted_groups(request.user)
        if form.is_valid() and group in permitted_groups:
            for fieldName in form.changed_data:
                if fieldName in settings.ALLSETTINGS: 
                    if fieldName in ['------','',None]:
                        deviceObj.deleteSetting(fieldName)
                    else:
                        deviceObj.putSetting(fieldName,form.cleaned_data[fieldName])
                elif fieldName == "inherits":
                    deviceObj.inherits = settingValue
                elif fieldName == "group":
                    groupObj = DjancidGroup(form.cleaned_data[fieldName])
                    deviceObj.rdbFile.deleteRouter(deviceObj.name)
                    deviceObj.parentGroup = groupObj
            deviceObj.save()
            if deviceObj.inherits:
                for fieldName,fieldValue in form.fields.items():
                    if fieldName in groupObj.allSettings.keys():
                        fieldValue.label = "{l} (i)".format(l=fieldValue.label)
            context['form'] = form
            context['device'] = deviceObj
            context['group'] = groupObj
            return(render(request,'rancid/DeviceDetails.html',context))
        else:
            raise(Http404("Permission Error"))

class ConfirmGroup(BaseView):
    def get(self,request,name):
        permitted_groups = get_permitted_groups(request.user)
        if name in permitted_groups:
            context = {}
            groupObj = DjancidGroup(name)
            if groupObj.devices:
                alsoDeleting = [DjancidDevice(dev['ip']) for dev in groupObj.devices]
                context['alsoDeleting'] = alsoDeleting
            context['group'] = groupObj
            return(render(request,'rancid/ConfirmGroup.html',context))
        else:
            raise(Http404("Permission Error"))

    def post(self,request,name):
        permitted_groups = get_permitted_groups(request.user)
        if name in permitted_groups:
            if request.POST.get("Delete"):
                groupObj = DjancidGroup(name)
                groupObj.delete()
            return(redirect('/'))


class ConfirmDevice(BaseView):
    def get(self,request,group,name):
        permitted_groups = get_permitted_groups(request.user)
        if group in permitted_groups:
            context = {}
            groupObj = DjancidGroup(group)
            device = self.b64_to_ip(name)
            deviceObj = DjancidDevice(device,groupObj)
            context['device'] = deviceObj
            context['group'] = groupObj
            return(render(request,'rancid/ConfirmDevice.html',context))
        else:
            raise(Http404("Permission Error"))

    def post(self,request,group,name):
        permitted_groups = get_permitted_groups(request.user)
        if group in permitted_groups:
            if request.POST.get("Delete"):
                groupObj = DjancidGroup(group)
                device = self.b64_to_ip(name)
                deviceObj = DjancidDevice(device,groupObj)
                deviceObj.delete()
            return(redirect('/'))
        else:
            raise(Http404("Permission Error"))


class Config(BaseView):
    def get(self,request,group,name):
        permitted_groups = get_permitted_groups(request.user)
        if group in permitted_groups:
            context = {}
            device = self.b64_to_ip(name)
            groupObj = DjancidGroup(group)
            deviceObj = DjancidDevice(device,groupObj)
            config = get_config(group,device)
            context['config'] = config.replace("\n","<br>")
            context['device'] = deviceObj
            context['group'] = groupObj
            return(render(request,'rancid/Config.html',context))
        else:
            raise(Http404("Permission Error"))


class Changes(BaseView):
    def get(self,request,group,name):
        permitted_groups = get_permitted_groups(request.user)
        if group in permitted_groups:
            device = self.b64_to_ip(name)
            groupObj = DjancidGroup(group)
            deviceObj = DjancidDevice(device,groupObj)
            context = {}
            diffs = get_config_diffs(group,device)
            context['diffs'] = diffs
            context['device'] = deviceObj
            context['group'] = groupObj
            return(render(request,'rancid/Changes.html',context))
        else:
            raise(Http404("Permission Error"))
