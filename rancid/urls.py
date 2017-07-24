from django.conf.urls import url
from .views import NewGroup 

urlpatterns = [
    url(r'addgroup/',NewGroup.as_view(),name="NewGroup"),
]
