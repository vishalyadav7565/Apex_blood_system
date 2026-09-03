from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q

from ambulance_apps.ambulance.models import Ambulance
from ambulance_apps.ambulance.serializers import (
    AmbulanceSerializer,
    AmbulanceRegisterSerializer,
)

try:
    from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiTypes
except ImportError:
    def extend_schema(*args, **kwargs):
        def decorator(f):
            return f
        return decorator
    OpenApiParameter = None
    OpenApiResponse = None
    OpenApiTypes = None


@extend_schema(
    tags=['Ambulance Management'],
    summary="Register a new Ambulance",
    description="Registers a new ambulance unit into the system by an Owner. Status defaults to pending admin review.",
    request=AmbulanceRegisterSerializer,
    responses={
        201: AmbulanceSerializer,
        400: OpenApiResponse(description="Bad Request - Validation Errors")
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_ambulance(request):
    """
    API endpoint for Owners to register a new ambulance.
    Sets default approval_status to 'pending_admin_review'.
    """
    serializer = AmbulanceRegisterSerializer(data=request.data)
    if serializer.is_valid():
        ambulance = serializer.save()
        return Response(
            {
                'message': 'Ambulance registered successfully and is pending admin approval.',
                'ambulance': AmbulanceSerializer(ambulance).data,
            },
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Ambulance Management'],
    summary="List registered Ambulances",
    description="Retrieves a list of registered ambulances with optional query filters.",
    parameters=[
        OpenApiParameter(name='status', type=OpenApiTypes.STR if OpenApiTypes else str, description='Filter by status: offline, online, busy, maintenance'),
        OpenApiParameter(name='approval_status', type=OpenApiTypes.STR if OpenApiTypes else str, description='Filter by approval status: pending_admin_review, approved, rejected'),
        OpenApiParameter(name='ambulance_type', type=OpenApiTypes.STR if OpenApiTypes else str, description='Filter by type: BLS, ALS, ICU, Neonatal, Patient Transport'),
        OpenApiParameter(name='is_available', type=OpenApiTypes.BOOL if OpenApiTypes else bool, description='Filter by availability (true/false)'),
        OpenApiParameter(name='is_active', type=OpenApiTypes.BOOL if OpenApiTypes else bool, description='Filter by active status (true/false)'),
        OpenApiParameter(name='owner_id', type=OpenApiTypes.INT if OpenApiTypes else int, description='Filter by Ambulance Owner ID'),
        OpenApiParameter(name='hospital_id', type=OpenApiTypes.INT if OpenApiTypes else int, description='Filter by hospital ID'),
        OpenApiParameter(name='search', type=OpenApiTypes.STR if OpenApiTypes else str, description='Search by vehicle number or registration number'),
    ] if OpenApiParameter else [],
    responses={200: AmbulanceSerializer(many=True)}
)
@api_view(['GET'])
@permission_classes([AllowAny])
def list_ambulances(request):
    """
    API endpoint to list registered ambulances with optional query filters.
    """
    queryset = Ambulance.objects.all().order_by('-created_at')

    status_param = request.query_params.get('status')
    if status_param:
        queryset = queryset.filter(status__iexact=status_param)

    approval_param = request.query_params.get('approval_status')
    if approval_param:
        queryset = queryset.filter(approval_status__iexact=approval_param)

    type_param = request.query_params.get('ambulance_type')
    if type_param:
        queryset = queryset.filter(ambulance_type__iexact=type_param)

    is_available = request.query_params.get('is_available')
    if is_available is not None:
        queryset = queryset.filter(is_available=is_available.lower() == 'true')

    is_active = request.query_params.get('is_active')
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active.lower() == 'true')

    owner_id = request.query_params.get('owner_id')
    if owner_id:
        queryset = queryset.filter(owner_id=owner_id)

    hospital_id = request.query_params.get('hospital_id')
    if hospital_id:
        queryset = queryset.filter(hospital_id=hospital_id)

    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(
            Q(vehicle_number__icontains=search) | Q(registration_number__icontains=search)
        )

    serializer = AmbulanceSerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Ambulance Management'],
    summary="Retrieve, Update or Delete an Ambulance",
    description="Manage an individual ambulance record by ID.",
    request=AmbulanceSerializer,
    responses={
        200: AmbulanceSerializer,
        204: OpenApiResponse(description="Deleted successfully") if OpenApiResponse else None,
        404: OpenApiResponse(description="Ambulance record not found") if OpenApiResponse else None,
    }
)
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def ambulance_detail(request, pk):
    """
    API endpoint to retrieve, update, or delete a specific ambulance record.
    """
    ambulance = get_object_or_404(Ambulance, pk=pk)

    if request.method == 'GET':
        serializer = AmbulanceSerializer(ambulance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method in ['PUT', 'PATCH']:
        partial = (request.method == 'PATCH')
        serializer = AmbulanceSerializer(ambulance, data=request.data, partial=partial)
        if serializer.is_valid():
            updated_ambulance = serializer.save()
            return Response(
                {
                    'message': 'Ambulance details updated successfully.',
                    'ambulance': AmbulanceSerializer(updated_ambulance).data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        ambulance.delete()
        return Response(
            {'message': 'Ambulance record deleted successfully.'},
            status=status.HTTP_204_NO_CONTENT,
        )


@extend_schema(
    tags=['Ambulance Management'],
    summary="Approve Ambulance by Admin",
    description="Approve an ambulance registered by an Owner, marking it active and approved.",
    responses={200: AmbulanceSerializer}
)
@api_view(['POST'])
@permission_classes([AllowAny])
def approve_ambulance(request, pk):
    """
    Admin endpoint to approve an ambulance registration.
    """
    ambulance = get_object_or_404(Ambulance, pk=pk)
    ambulance.is_approved = True
    ambulance.approval_status = "approved"
    ambulance.is_active = True
    ambulance.rejection_reason = None
    ambulance.save()
    return Response(
        {
            'message': 'Ambulance approved successfully.',
            'ambulance': AmbulanceSerializer(ambulance).data,
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(
    tags=['Ambulance Management'],
    summary="Reject Ambulance by Admin",
    description="Reject an ambulance registration with an optional rejection reason.",
    responses={200: AmbulanceSerializer}
)
@api_view(['POST'])
@permission_classes([AllowAny])
def reject_ambulance(request, pk):
    """
    Admin endpoint to reject an ambulance registration.
    """
    ambulance = get_object_or_404(Ambulance, pk=pk)
    reason = request.data.get('rejection_reason', 'Registration rejected by admin.')
    ambulance.is_approved = False
    ambulance.approval_status = "rejected"
    ambulance.is_active = False
    ambulance.rejection_reason = reason
    ambulance.save()
    return Response(
        {
            'message': 'Ambulance rejected.',
            'ambulance': AmbulanceSerializer(ambulance).data,
        },
        status=status.HTTP_200_OK,
    )
