from django.conf.urls import url
from .views import NewGroup,GroupDetails,NewDevice,DeviceDetails,ConfirmGroup,ConfirmDevice,Config,Changes

urlpatterns = [
    url(r'addgroup/',NewGroup.as_view(),name='NewGroup'),
    url(r'groupdetails/(?P<group>.*)',GroupDetails.as_view(),name='GroupDetails'),
    url(r'adddevice/(?P<group>.*)',NewDevice.as_view(),name='NewDevice'),
    url(r'devicedetails/(?P<group>.*)/(?P<device>.*)/',DeviceDetails.as_view(),name='DeviceDetails'),
    url(r'confirmgroup/(?P<name>.*)/',ConfirmGroup.as_view(),name='ConfirmGroup'),
    url(r'confirmdevice/(?P<group>.*)/(?P<name>.*)/',ConfirmDevice.as_view(),name='ConfirmDevice'),
    url(r'config/(?P<group>.*)/(?P<name>.*)/',Config.as_view(),name='Config'),
    url(r'changes/(?P<group>.*)/(?P<name>.*)/',Changes.as_view(),name='Changes'),
]
