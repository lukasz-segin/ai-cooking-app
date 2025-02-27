from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentProcessorViewSet

router = DefaultRouter()
router.register(r'documents', DocumentProcessorViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 