"""
URL configuration for edutech project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from core import urls as core_urls
from users import urls as users_urls
from academico import urls as academico_urls
from portal import urls as portal_urls
from portal.views import portal_redirect_view


urlpatterns = [
    path('', portal_redirect_view, name='home'),
    path('admin/', admin.site.urls),
    path('users/', include(users_urls)),
    path('academico/', include(academico_urls)),
    path('portal/', include(portal_urls)),

]
