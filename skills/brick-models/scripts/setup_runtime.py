#!/usr/bin/env python3
"""Install isolated Python dependencies and, if missing, an official portable Blender."""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import venv
import zipfile
from pathlib import Path
from runtime import find_blender, runtime_home

VERSION = '5.2.0'
BASE = 'https://download.blender.org/release/Blender5.2/'
PACKAGES = {
    ('Darwin', 'arm64'): ('macos-arm64.dmg', 'ed4d8390166dec5ea0a2813a03db6221f206ce016442be7f59f41d760972568a'),
    ('Linux', 'x86_64'): ('linux-x64.tar.xz', '96f6c181a30f4950607839dc84d42a354b250d8a0231b098b59b7bc69c351c48'),
    ('Windows', 'x86_64'): ('windows-x64.zip', '2d184b626c001692c362291911293b6a297179d618d95e9e9192c3a80318adc4'),
    ('Windows', 'arm64'): ('windows-arm64.zip', 'c00b6a5d80456d9299865ab4db730b7c93b0af4ae77d707548f886692786d881'),
}


def package(system=None, machine=None):
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    machine = {'amd64': 'x86_64', 'aarch64': 'arm64'}.get(machine, machine)
    if (system, machine) not in PACKAGES:
        raise ValueError(f'No managed Blender package for {system}/{machine}. Install a compatible official Blender and set BLENDER_BIN.')
    suffix, checksum = PACKAGES[system, machine]
    return f'blender-{VERSION}-{suffix}', checksum


def download(url, dest, checksum):
    digest = hashlib.sha256()
    if shutil.which('curl'):
        subprocess.run(['curl', '-fLsS', '--connect-timeout', '30', '--max-time', '1200', '--retry', '2', '--output', str(dest), url], check=True)
    else:
        request = urllib.request.Request(url, headers={'User-Agent': 'BrickModels/0.1'})
        with urllib.request.urlopen(request, timeout=60) as response, dest.open('wb') as target:
            shutil.copyfileobj(response, target)
    with dest.open('rb') as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    if digest.hexdigest() != checksum:
        raise ValueError('Blender download checksum mismatch; refusing to unpack or run it')


def unpack(archive, stage):
    payload = stage / 'payload'
    payload.mkdir()
    if archive.suffix == '.dmg':
        mount = stage / 'mount'
        mount.mkdir()
        subprocess.run(['hdiutil', 'attach', str(archive), '-readonly', '-nobrowse', '-mountpoint', str(mount)], check=True, stdout=subprocess.DEVNULL)
        try:
            subprocess.run(['ditto', str(mount/'Blender.app'), str(payload/'Blender.app')], check=True)
        finally:
            subprocess.run(['hdiutil', 'detach', str(mount)], check=True, stdout=subprocess.DEVNULL)
        return payload
    if archive.suffix == '.zip':
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                if not (payload / name).resolve().is_relative_to(payload.resolve()):
                    raise ValueError('Unsafe archive path')
            z.extractall(payload)
    else:
        with tarfile.open(archive) as t:
            t.extractall(payload, filter='data')
    children = list(payload.iterdir())
    if len(children) != 1 or not children[0].is_dir():
        raise ValueError('Unexpected Blender archive structure')
    return children[0]


def install_blender(root):
    name, checksum = package()
    destination = root/'blender'
    if destination.exists():
        raise ValueError('Managed Blender folder is incomplete; choose a new runtime directory or repair it explicitly')
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < 3 * 1024**3:
        raise ValueError('At least 3 GiB of free space is needed to download and unpack Blender')
    print('Downloading official Blender (approximately 350–410 MB) into the user runtime.', file=sys.stderr, flush=True)
    with tempfile.TemporaryDirectory(prefix='.blender-install-', dir=root) as tmp:
        stage = Path(tmp)
        archive = stage/name
        download(BASE+name, archive, checksum)
        unpack(archive, stage).rename(destination)
    return find_blender(root=root, system=False)


def setup(root, portable=False, blender=None):
    if sys.version_info < (3, 11):
        raise ValueError('Python 3.11 or newer is required')
    root = root.expanduser().resolve()
    skill = Path(__file__).resolve().parents[1]
    if root.is_relative_to(skill) or any((p/'.git').exists() for p in (root, *root.parents)):
        raise ValueError('Place the runtime outside skill and application repositories')
    try:
        binary = find_blender(blender, root, system=not portable)
    except ValueError:
        if blender:
            raise
        binary = install_blender(root)
    version = subprocess.run([binary, '--version'], check=True, capture_output=True, text=True, timeout=30).stdout.splitlines()[0]
    env = root/'python'
    python = env/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.is_file():
        venv.EnvBuilder(with_pip=True).create(env)
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(skill/'requirements.txt')], check=True, stdout=sys.stderr)
    # Blender can start yet fail to render on an unsupported GPU/OS; the first build is still a separate check.
    print(json.dumps({'python': str(python), 'blender': binary, 'blender_version': version,
                      'runtime': str(root), 'render_test': 'not_run'}, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime-dir', type=Path, default=runtime_home())
    p.add_argument('--portable', action='store_true', help='Use an isolated Blender even if a system copy exists')
    p.add_argument('--blender', help='Use an explicit existing executable')
    a = p.parse_args()
    try:
        setup(a.runtime_dir, a.portable, a.blender)
    except (ValueError, OSError, subprocess.SubprocessError) as e:
        print(f'Setup failed: {e}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
