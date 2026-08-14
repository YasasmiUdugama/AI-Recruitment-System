from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('parser/', include('parser.urls')),
    path('ranking/', include('ranking.urls')),
    path('interview/', include('interview.urls')),
    path('voice/', include('voice.urls')),
    path('emotion/', include('emotion.urls')),
    path('emailer/', include('emailer.urls')),
    path('shortlist/', include('shortlist.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
