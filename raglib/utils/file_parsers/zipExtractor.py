from contextlib import contextmanager
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from pathlib import Path

@contextmanager
def extracted_zip(zip_file: Path) -> Path:
    """
    Exctracts the content of a zip file a context manager, returning the path the the newly created folder.
    After leaving the context manager, the folder will be deleted!
    """
    tmp_path = TemporaryDirectory()
    
    
    with ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(tmp_path)

    yield tmp_path

    tmp_path.cleanup()