from rest_framework.permissions import BasePermission


class IsCustomer(BasePermission):
    message = "You need a customer profile to do this."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and not user.is_suspended
            and hasattr(user, "customer_profile")
        )
