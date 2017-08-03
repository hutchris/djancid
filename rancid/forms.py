from django import forms
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from rancid.lib.fileops import get_device_types
from rancid.lib.main import get_permitted_groups 


def password_validator(value):
    badValues = ["{","}"," ","\\"]
    for badValue in badValues:
        if badValue in value:
            raise(ValidationError("Field cannot contain {bvs}".format(badValues)))


class GroupForm(forms.Form):
    name = forms.CharField(label="Group Name*",required=True)
    deviceType = forms.ChoiceField(label="Device Type",required=False)
    status = forms.BooleanField(initial=True,label="Enable Backups",required=False)
    user = forms.CharField(max_length=100,label="Username",required=False)
    password = forms.CharField(widget=forms.PasswordInput(render_value=True),max_length=128,label="Password",required=False,validators=[password_validator])
    enablepassword = forms.CharField(widget=forms.PasswordInput(render_value=True),max_length=128,label="Enable Password",required=False,validators=[password_validator])
    method = forms.ChoiceField(choices=(("SSH","SSH"),("Telnet","Telnet")),label="Connection Method",required=False)
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
    def __init__(self,*args,**kwargs):
        super(GroupForm,self).__init__(*args,**kwargs)
        self.fields["deviceType"].choices = [('------','------')] + [(d,d) for d in get_device_types()]
        groups = Group.objects.all()
        for groupObj in groups:
            fieldName = "perm_{gn}".format(gn=groupObj.name)
            self.fields[fieldName] = forms.BooleanField(initial=True,label="Group Access: {gn}".format(gn=groupObj.name))
            self.fields[fieldName].required = False


class DeviceForm(forms.Form):
    ip = forms.CharField(max_length=100,label="IP/Hostname*",required=True)
    group = forms.ChoiceField(label="Group*",required=True)
    inherits = forms.BooleanField(label="Inherit Group Settings*",initial=True,required=True)
    deviceType = forms.ChoiceField(label="Device Type*",required=True)
    status = forms.BooleanField(initial=True,label="Enable Backups*",required=True)
    user = forms.CharField(max_length=100,label="Username*",required=True)
    password = forms.CharField(widget=forms.PasswordInput(render_value=True),max_length=128,label="Password*",required=True,validators=[password_validator])
    enablepassword = forms.CharField(widget=forms.PasswordInput(render_value=True),max_length=128,label="Enable Password",required=False,validators=[password_validator])
    method = forms.ChoiceField(choices=(("SSH","SSH"),("Telnet","Telnet")),label="Connection Method*",required=True)
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
    def __init__(self,djangoUser,*args,**kwargs):
        super(DeviceForm,self).__init__(*args,**kwargs)
        self.fields["group"].choices = [('------','------')] + [(g,g) for g in get_permitted_groups(djangoUser)]
        self.fields["deviceType"].choices = [('------','------')] + [(d,d) for d in get_device_types()]
