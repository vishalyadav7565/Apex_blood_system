from rest_framework import permissions


class IsDriverOrOwner(permissions.BasePermission):
    """
    Custom permission to only allow drivers to access/edit their own profiles,
    and associated hospital owners to view their linked driver accounts.
    """
    def has_object_permission(self, request, view, obj):
        # Allow if the user matches the driver phone number
        if hasattr(request.user, 'phone') and request.user.phone == obj.phone:
            return True
            
        # Allow if the user is the hospital owner of the linked ambulance
        if hasattr(request.user, 'hospital') and obj.ambulance and obj.ambulance.hospital == request.user.hospital:
            return True
            
        return False
