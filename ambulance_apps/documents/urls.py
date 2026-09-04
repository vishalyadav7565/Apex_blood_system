from django.urls import path
from .views import (
    CreateVerificationSessionView,
    GetVerificationSessionView,
    UpdateVerificationSessionView,
    ProcessDocumentView
)

urlpatterns = [
    path('session/create/', CreateVerificationSessionView.as_view(), name='create_verification_session'),
    path('session/<str:session_code>/', GetVerificationSessionView.as_view(), name='get_verification_session'),
    path('session/<str:session_code>/update/', UpdateVerificationSessionView.as_view(), name='update_verification_session'),
    path('process/', ProcessDocumentView.as_view(), name='process_document'),
]

