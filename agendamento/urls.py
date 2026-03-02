from django.urls import path
from . import views
from smartwash.admin_site import admin_site


urlpatterns = [
    path("admin/", admin_site.urls),
    path("", views.agendar, name="agendar"),
    path("sucesso/", views.sucesso, name="sucesso"),

]