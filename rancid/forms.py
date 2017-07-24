from django import forms
from django.contrib.auth.models import Group


class ValidSettings(forms.Form):
    deviceType = forms.ChoiceField(label="Device Type",required=True)
    status = forms.BooleanField(initial=True,label="Enable Backups",required=True)
    user = forms.CharField(max_length=100,label="Username",required=True)
    password = forms.CharField(widget=forms.PasswordInput,max_length=128,label="Password",required=True)
    method = forms.ChoiceField(choices=(("SSH","SSH"),("Telnet","Telnet")),label="Connection Method",required=True)
    noenable = forms.BooleanField(initial=True,label="No Enable",required=False)
    autoenable = forms.BooleanField(initial=True,label="Auto Enable",required=False)
    prompt = forms.CharField(label="Prompt",required=False)
    passphrase = forms.CharField(label="Passphrase",required=False)
    passprompt = forms.CharField(label="Passprompt",required=False)
    sshcmd = forms.CharField(label="SSH Command",required=False)
    timeout = forms.IntegerField(label="Timeout",max_value=30,min_value=1,required=False)
    cyphertype = forms.CharField(label="Cypher Type",required=False)
    enableprompt = forms.CharField(label="Enable Prompt",required=False)
    enablecmd = forms.CharField(label="Enable Command",required=False)
    enauser = forms.CharField(label="Enable User",required=False)
    identity = forms.CharField(label="Identity (keyfile)",required=False)


class GroupForm(ValidSettings):
    def __init__(self,*args,**kwargs):
        super(ValidSettings,self).__init__(*args,**kwargs)
        groups = Group.objects.all()
        for groupObj in groups:
            self.fields["perm_{gn}".format(gn=groupObj.name)] = form.BooleanField(initial=True,label=groupObj.name)
    name = forms.CharField()

class DeviceForm(ValidSettings):
    ip = forms.CharField(max_length=100,label="IP/Hostname",required=True)
    group = forms.ChoiceField(label="Group",required=True)
    inherit = forms.BooleanField(label="Inherit Group Settings",initial=True,required=True)
