from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from academics.api_support import not_found, server_error

handler404 = not_found
handler500 = server_error

urlpatterns = [
    path('api/v1/', include('academics.urls')),
    path('api/schema', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
