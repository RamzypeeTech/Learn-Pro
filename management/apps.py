from django.apps import AppConfig


class ManagementConfig(AppConfig):
    name = 'management'

    def ready(self):
        from . import signals  # noqa: F401
