"""Content-aware validation for spreadsheet imports."""
from __future__ import annotations

import csv
import io
import zipfile

from django.core.exceptions import ValidationError


OLE_SIGNATURE = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
ZIP_SIGNATURES = (b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08')
MAX_ARCHIVE_ENTRIES = 2500
MAX_ARCHIVE_UNCOMPRESSED = 64 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200


def _ext(name: str) -> str:
    return '.' + name.rsplit('.', 1)[-1].lower() if '.' in (name or '') else ''


def _read_all(uploaded_file, max_bytes: int) -> bytes:
    if getattr(uploaded_file, 'size', 0) > max_bytes:
        raise ValidationError(f'Fichier trop volumineux (maximum {max_bytes // (1024 * 1024)} Mo).')
    pos = uploaded_file.tell() if hasattr(uploaded_file, 'tell') else None
    try:
        if hasattr(uploaded_file, 'seek'):
            uploaded_file.seek(0)
        data = uploaded_file.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValidationError('Fichier trop volumineux.')
        return bytes(data)
    finally:
        if hasattr(uploaded_file, 'seek'):
            uploaded_file.seek(pos or 0)


def _validate_zip_container(data: bytes) -> None:
    if not data.startswith(ZIP_SIGNATURES):
        raise ValidationError('Le contenu ne correspond pas à un classeur Office Open XML.')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_ENTRIES:
                raise ValidationError('Classeur refusé : archive contenant trop de fichiers internes.')
            uncompressed = 0
            for info in infos:
                path = info.filename.replace('\\', '/')
                if path.startswith('/') or '..' in path.split('/'):
                    raise ValidationError('Classeur refusé : chemin interne invalide.')
                uncompressed += info.file_size
                if uncompressed > MAX_ARCHIVE_UNCOMPRESSED:
                    raise ValidationError('Classeur refusé : contenu décompressé trop volumineux.')
                if info.file_size and info.compress_size == 0:
                    raise ValidationError('Classeur refusé : archive compressée anormale.')
                if info.compress_size and (info.file_size / info.compress_size) > MAX_COMPRESSION_RATIO:
                    raise ValidationError('Classeur refusé : taux de compression anormal.')
            names = {info.filename for info in infos}
            if '[Content_Types].xml' not in names:
                raise ValidationError('Le fichier ZIP fourni n’est pas un classeur Office valide.')
    except zipfile.BadZipFile as exc:
        raise ValidationError('Classeur Office corrompu ou invalide.') from exc


def validate_spreadsheet_upload(
    uploaded_file,
    *,
    allowed_extensions=('.xlsx', '.xls', '.csv'),
    max_bytes=10 * 1024 * 1024,
):
    """Validate extension, magic/container structure and archive expansion limits."""
    extension = _ext(getattr(uploaded_file, 'name', ''))
    allowed = {item.lower() for item in allowed_extensions}
    if extension not in allowed:
        raise ValidationError(
            'Format non autorisé. Formats acceptés : ' + ', '.join(sorted(allowed))
        )

    data = _read_all(uploaded_file, max_bytes)
    if extension in {'.xlsx', '.xlsm'}:
        _validate_zip_container(data)
    elif extension == '.xls':
        if not data.startswith(OLE_SIGNATURE):
            raise ValidationError('Le contenu ne correspond pas à un fichier Excel .xls valide.')
    elif extension == '.csv':
        if b'\x00' in data:
            raise ValidationError('CSV invalide : octets nuls détectés.')
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text = data.decode('cp1252')
            except UnicodeDecodeError as exc:
                raise ValidationError('CSV illisible : encodage non pris en charge.') from exc
        # Parse a small sample to reject binary files renamed as CSV.
        try:
            sample = text[:8192]
            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|') if sample.strip() else csv.excel
            next(csv.reader(io.StringIO(sample), dialect), None)
        except csv.Error as exc:
            raise ValidationError('Le contenu ne correspond pas à un CSV valide.') from exc

    if hasattr(uploaded_file, 'seek'):
        uploaded_file.seek(0)
    return uploaded_file
