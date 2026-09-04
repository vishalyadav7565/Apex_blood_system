from django.urls import path
from .views import (
    CreateVerificationSessionView,
    GetVerificationSessionView,
    UpdateVerificationSessionView,
    UploadAadhaarView,
    UploadSelfieView,
    CompleteVerificationView,
    CancelVerificationSessionView,
    ProcessDocumentView
)

urlpatterns = [
    path('session/create/', CreateVerificationSessionView.as_view(), name='create_verification_session'),
    path('session/<str:session_code>/', GetVerificationSessionView.as_view(), name='get_verification_session'),
    path('session/<str:session_code>/update/', UpdateVerificationSessionView.as_view(), name='update_verification_session'),
    path('session/<str:session_code>/cancel/', CancelVerificationSessionView.as_view(), name='cancel_verification_session'),
    path('aadhaar/', UploadAadhaarView.as_view(), name='upload_aadhaar'),
    path('selfie/', UploadSelfieView.as_view(), name='upload_selfie'),
    path('complete/', CompleteVerificationView.as_view(), name='complete_verification'),
    path('process/', ProcessDocumentView.as_view(), name='process_document'),
]


