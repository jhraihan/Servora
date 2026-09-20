from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateMediaStorage(FileSystemStorage):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("location", settings.PRIVATE_MEDIA_ROOT)
        kwargs.setdefault("base_url", None)
        super().__init__(*args, **kwargs)

    def url(self, name):
        raise NotImplementedError(
            "Private media has no public URL. Serve it through an "
            "authenticated view."
        )


private_media_storage = PrivateMediaStorage()
