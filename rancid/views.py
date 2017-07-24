import os
from base64 import b64encode,b64decode
from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from rancid.lib.main import DjancidGroup,DjancidDevice
from rancid.lib.fileops import RancidConf,Cloginrc,RouterDB
from rancid.models import RancidGroupPermission
from rancid.forms import GroupForm,DeviceForm

rcFile = RancidConf()

class BaseView(View):
    def get_permitted_groups(self,user):
        if user.is_staff():
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

    def get_device_types(self):
        filePath = os.path.join(settings.RANCID_SETTINGS_DIR,'rancid.types.base')
        with open(filePath,"r") as f:
            lines = f.readlines()
        typesRaw = [line.split(";")[0] for line in lines if ";" in line and "#" not in line]
        types = list(set(typesRaw))
        types.sort()
        return(types)

class NewGroup(BaseView,LoginRequiredMixin):
    def get(self,request):
        form = GroupForm()
        form.fields['deviceType'].choices = [(dtype,dtype) for dtype in self.get_device_types()]
        form.initial['deviceType'] = "cisco"
        context = {'form':form}
        return(render(request,'rancid/NewGroup.html',context))

    def post(self,request):
        form = GroupForm(request.POST)
        if form.is_valid():
            groupObj = DjancidGroup(form.cleaned_data['name'])
            for settingName,settingValue in form.cleaned_data.items():
                if settingName in setting.ALLSETTINGS:
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
            return(HttpResponse("Invalid Data"))
        return(redirect("GroupDetails",group=groupObj.name))
