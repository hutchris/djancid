import os
from git import Repo
from rancid.lib.fileops import RancidConf
from django.conf import settings

confFile = RancidConf()

def get_config(group,device):
    configFile = os.path.join(settings.RANCID_ROOT,group,'configs',device)
    if os.path.exists(configFile):
        with open(configFile,"r") as f:
            config = f.read()
        return(config)
    else:
        return("No configuration backups have been made for this device")

def get_config_diffs(group,device):
    repoDir = os.path.join(settings.RANCID_ROOT,group)
    repo = Repo(repoDir)
    commits = list(repo.iter_commits())
    configFile = os.path.join('configs',device)
    diffs = []
    for i,commit in enumerate(commits):
        if commit != commits[-1]:
            diff = {}
            text = repo.git.diff(commits[i+1],commit,configFile)
            if text:
                diff['text'] = text.replace("\n","<br>")
                diff['datetime'] = commit.committed_datetime.isoformat()
                diffs.append(diff)
    return(diffs)
