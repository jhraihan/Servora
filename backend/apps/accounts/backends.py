from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from .validators import normalise_bd_phone

User = get_user_model()

class PhoneOrEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("phone") or kwargs.get("email")
        if not identifier or not password:
            return None

        lookup = Q(email__iexact=identifier.strip())
        if "@" not in identifier:
            lookup = Q(phone=normalise_bd_phone(identifier))

        try:
            user = User.objects.get(lookup)
        except User.DoesNotExist:
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
