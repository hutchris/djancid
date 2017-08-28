# djancid
Django front-end for rancid

The purpose of this project is to make RANCID (device configuration backup software) http://www.shrubbery.net/rancid/ easier to manage and restrict the access that some users have.

Functions:
1. Control logins using Django's built-in user and group models, controlled via the admin page
2. Attach Django groups to rancid group so users can only see certain devices
3. Create, edit and delete devices
4. Create, edit and delete RANCID groups
5. RANCID device settings can be configured on groups and then inherited to the devices in that group
6. View most recent configuration backup
7. View GIT diff for all changes

(work in progress)

Installation onto Ubuntu 16.04 (Will expand)
1. Install RANCID
  a. sudo apt-get install rancid
2. Install Apache
3. Setup Apache with mod-wsgi to run Django
4. Change Apache to run as the rancid user
5. Give the rancid user permission to read/write rancid.conf
6. Install Django
7. Clone this repo
8. Setup a database for Django
9. Configure local_settings.py
