from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.i18n import set_language
from appointments import views as appt_views

admin.site.site_header = "My Doctor"
admin.site.site_title = "My Doctor"
admin.site.index_title = "Administration"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/setlang/', set_language, name='set_language'),
    path('', appt_views.home, name='home'),
    path('tableau-de-bord/', appt_views.dashboard, name='dashboard'),
    path('', include('accounts.urls')),
    path('', include('appointments.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)