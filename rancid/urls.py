from django.conf.urls import url
from .views import NewGroup,GroupDetails,NewDevice,DeviceDetails

urlpatterns = [
    url(r'addgroup/',NewGroup.as_view(),name='NewGroup'),
    url(r'groupdetails/(?P<group>.*)',GroupDetails.as_view(),name='GroupDetails'),
    url(r'adddevice/(?P<group>.*)',NewDevice.as_view(),name='NewDevice'),
    url(r'devicedetails/(?P<group>.*)/(?P<device>.*)',DeviceDetails.as_view(),name='DeviceDetails'),
]
