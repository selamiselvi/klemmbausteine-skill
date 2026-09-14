"""Standard-library runtime discovery shared by setup and the model pipeline."""
import os
import platform
import shutil
from pathlib import Path


def runtime_home():
    if os.environ.get('BRICK_MODELS_RUNTIME'):
        return Path(os.environ['BRICK_MODELS_RUNTIME']).expanduser().resolve()
    if platform.system() == 'Windows':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local'))
    elif platform.system() == 'Darwin':
        base = Path.home() / 'Library/Caches'
    else:
        base = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))
    return base / 'brick-models'


def find_blender(explicit=None, root=None, system=True):
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise ValueError('The explicit Blender executable does not exist')
        return str(path)
    root = Path(root) if root else runtime_home()
    choices = []
    if system:
        choices.extend([os.environ.get('BLENDER_BIN'), shutil.which('blender'),
                        str(Path.home() / 'Applications/Blender.app/Contents/MacOS/Blender'),
                        '/Applications/Blender.app/Contents/MacOS/Blender'])
        for base in (os.environ.get('ProgramFiles'), os.environ.get('LOCALAPPDATA')):
            if base:
                choices.extend(sorted(Path(base).glob('Blender Foundation/Blender */blender.exe'), reverse=True))
    choices.extend([root/'blender/Blender.app/Contents/MacOS/Blender',
                    root/'blender/blender', root/'blender/blender.exe'])
    for choice in choices:
        if choice and Path(choice).is_file():
            return str(Path(choice).resolve())
    raise ValueError('Blender not found. Run scripts/setup_runtime.py, or pass --blender PATH.')
