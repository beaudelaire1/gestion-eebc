from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.functional import cached_property
from django.utils.deconstruct import deconstructible


CLOUDINARY_RESOURCE_TYPES = ('raw', 'image', 'video')


@deconstructible
class DocumentStorage(Storage):
    """Storage for user-uploaded documents, including raw ZIP-based files."""

    @cached_property
    def backend(self):
        if getattr(settings, 'CLOUDINARY_URL', ''):
            from cloudinary_storage.storage import RawMediaCloudinaryStorage

            return RawMediaCloudinaryStorage()

        return FileSystemStorage()

    @cached_property
    def cloudinary_read_backends(self):
        from cloudinary_storage.storage import MediaCloudinaryStorage, RawMediaCloudinaryStorage, VideoMediaCloudinaryStorage

        return (
            RawMediaCloudinaryStorage(),
            MediaCloudinaryStorage(),
            VideoMediaCloudinaryStorage(),
        )

    def _open(self, name, mode='rb'):
        try:
            return self.backend.open(name, mode)
        except Exception:
            if not getattr(settings, 'CLOUDINARY_URL', ''):
                raise

        for backend in self.cloudinary_read_backends:
            try:
                return backend.open(name, mode)
            except Exception:
                continue

        signed_file = self._open_signed_cloudinary(name, mode)
        if signed_file is not None:
            return signed_file

        return self.backend.open(name, mode)

    def _save(self, name, content):
        return self.backend.save(name, content)

    def delete(self, name):
        return self.backend.delete(name)

    def exists(self, name):
        return self.backend.exists(name)

    def listdir(self, path):
        return self.backend.listdir(path)

    def size(self, name):
        return self.backend.size(name)

    def url(self, name):
        return self.backend.url(name)

    def path(self, name):
        return self.backend.path(name)

    def get_accessed_time(self, name):
        return self.backend.get_accessed_time(name)

    def get_created_time(self, name):
        return self.backend.get_created_time(name)

    def get_modified_time(self, name):
        return self.backend.get_modified_time(name)

    def _open_signed_cloudinary(self, name, mode):
        import requests

        try:
            from cloudinary.utils import private_download_url
        except ImportError:
            return None

        extension = self._get_extension(name)
        if not extension:
            return None

        for resource_type in CLOUDINARY_RESOURCE_TYPES:
            for public_id in self._public_id_candidates(name):
                url = private_download_url(
                    public_id,
                    extension,
                    resource_type=resource_type,
                    type='upload',
                    attachment=False,
                )
                try:
                    response = requests.get(url, timeout=30)
                except requests.RequestException:
                    continue
                if response.status_code == 404:
                    continue
                if response.status_code in (401, 403):
                    continue
                try:
                    response.raise_for_status()
                except requests.RequestException:
                    continue
                file_obj = ContentFile(response.content)
                file_obj.name = name
                file_obj.mode = mode
                return file_obj

        return None

    @staticmethod
    def _get_extension(name):
        filename = name.rsplit('/', 1)[-1]
        if '.' not in filename:
            return ''
        return filename.rsplit('.', 1)[-1].lower()

    @staticmethod
    def _public_id_candidates(name):
        normalized = name.replace('\\', '/')
        candidates = [normalized]
        filename = normalized.rsplit('/', 1)[-1]
        if '.' in filename:
            without_extension = normalized.rsplit('.', 1)[0]
            candidates.append(without_extension)
        if normalized.startswith('media/'):
            candidates.append(normalized[len('media/'):])
        return tuple(dict.fromkeys(candidates))


document_storage = DocumentStorage()
