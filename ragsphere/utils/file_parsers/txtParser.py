from pathlib import Path
import re

def parse_txt(path: Path) -> str:
    """
    Reads the content of a .txt file.

    Parameters:
    - path (Path): the path to the .txt file

    Returns:
    The content of the .txt file
    """
    document = ""

    # Reads content of the .txt file
    with open(path, "r") as file:
        document = file.read()

    # Cleanup txt data
    document = re.sub(r'\.\.\.+', '...', document)
    document = re.sub(r' +',' ', document)
    document = re.sub(r'\n ','\n', document)
    document = re.sub(r'\n+','\n', document).strip()

    return [document]