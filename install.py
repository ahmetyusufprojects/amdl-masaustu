#!/usr/bin/python3
"""Kullanıcıya özel masaüstü kısayolu ve isteğe bağlı motor kurulumu."""
import argparse
import hashlib
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import tempfile
import urllib.request
import zipfile

import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk  # noqa: F401

from engine import write_yaml
from settings import FIELDS, put

ROOT = Path(__file__).resolve().parent
APP = 'io.github.AmdlMasaustu'
AMDL = 'https://github.com/zhaarey/apple-music-downloader/releases/download/v0.1.4/amdl_linux_amd64'
AMDL_SHA = '1a3a4000edd74be98efccf7f611b97d47ef822d8e059805c6aaaef98f0477747'
ARTIFACT = 'repos/WorldObservationLog/wrapper/actions/artifacts/13565793609/zip'
WRAPPER_SHA = 'efa69efab16b188ff486f26e9278c94938f9cecc3dd15e3e8c11b5270fa54d04'


def verify(path, digest):
    with path.open('rb') as f:
        if hashlib.file_digest(f, 'sha256').hexdigest() != digest:
            raise ValueError('SHA-256 eşleşmedi; kurulum durduruldu.')


def fetch(runtime):
    if platform.machine() != 'x86_64':
        raise ValueError('Otomatik motor kurulumu yalnızca Linux x86_64 için hazır.')
    if (runtime / 'amdl').exists() or (runtime / 'wrapper-lite').exists():
        raise ValueError('Motor dizini zaten var; mevcut dosyalar değiştirilmedi.')
    if not shutil.which('gh'):
        raise ValueError('Otomatik indirme için GitHub CLI (gh) gerekir.')
    runtime.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix='.amdl-motor-', dir=runtime.parent) as tmp:
        temp = Path(tmp)
        with urllib.request.urlopen(AMDL, timeout=40) as remote, (temp / 'amdl').open('wb') as local:
            shutil.copyfileobj(remote, local)
        verify(temp / 'amdl', AMDL_SHA)
        archive = temp / 'wrapper.zip'
        with archive.open('wb') as local:
            subprocess.run(['gh', 'api', ARTIFACT], stdout=local, check=True)
        verify(archive, WRAPPER_SHA)
        extracted = temp / 'wrapper-lite'
        extracted.mkdir(mode=0o700)
        with zipfile.ZipFile(archive) as zipped:
            if any(Path(i.filename).is_absolute() or '..' in Path(i.filename).parts or
                   stat.S_ISLNK(i.external_attr >> 16) for i in zipped.infolist()):
                raise ValueError('Paket güvenli olmayan bir yol içeriyor.')
            zipped.extractall(extracted)
        for binary in (temp / 'amdl', extracted / 'wrapper-lite-qemu', extracted / 'qemu/bin/qemu-system-x86_64'):
            binary.chmod(0o700)
        runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
        (temp / 'amdl').rename(runtime / 'amdl')
        extracted.rename(runtime / 'wrapper-lite')


def quote_exec(text):
    if any(c in text for c in '\n\r\x00'):
        raise ValueError('Masaüstü yolunda geçersiz karakter.')
    escaped = ''.join('\\' + c if c in '\\"`$' else c for c in text).replace('%', '%%')
    return '"' + escaped.replace('\\', '\\\\') + '"'


def install(args, base, xdg):
    runtime = args.runtime.resolve()
    if args.fetch:
        fetch(runtime)
    for path in (runtime / 'amdl', runtime / 'wrapper-lite/wrapper-lite-qemu',
                 runtime / 'wrapper-lite/qemu/bin/qemu-system-x86_64'):
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError('Motor eksik. --runtime ile hazır motor klasörünü göster veya --fetch kullan.')
    config = runtime / 'config.yaml'
    if not config.exists():
        defaults = {}
        for path, value, *_ in FIELDS:
            put(defaults, path, value)
        write_yaml(config, defaults)
    appdir = base / 'uygulama'
    appdir.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in ('desktop.py', 'engine.py', 'settings.py', 'icon.svg'):
        shutil.copyfile(ROOT / name, appdir / name)
    desktop_dir = xdg / 'applications'
    desktop_dir.mkdir(parents=True, exist_ok=True)
    icons = xdg / 'icons' / 'hicolor' / 'scalable' / 'apps'
    icons.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / 'icon.svg', icons / (APP + '.svg'))
    exec_line = ' '.join(quote_exec(str(x)) for x in ('/usr/bin/python3', '-Es', appdir / 'desktop.py', '--runtime', runtime))
    content = f'''[Desktop Entry]
Type=Application
Name=amdl Masaüstü
Name[en]=amdl Desktop
Comment=Apple Music indirme merkezi
Comment[en]=Apple Music download center
Exec={exec_line}
Icon={APP}
Terminal=false
Categories=AudioVideo;Audio;
StartupNotify=true
'''
    desktop_file = desktop_dir / (APP + '.desktop')
    desktop_file.write_text(content, encoding='utf-8')
    desktop_file.chmod(0o644)
    if shutil.which('desktop-file-validate'):
        subprocess.run(['desktop-file-validate', desktop_file], check=True)
    if shutil.which('update-desktop-database'):
        subprocess.run(['update-desktop-database', desktop_dir], check=False)
    print('Kuruldu. Uygulama menüsünden “amdl Masaüstü”nü aç.')


def main():
    os.umask(0o077)
    xdg = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
    base = xdg / 'amdl-masaustu'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, default=base / 'motor', help='amdl ve wrapper-lite klasörü')
    parser.add_argument('--fetch', action='store_true', help='Sabitlenmiş Linux paketlerini doğrulayarak indir')
    try:
        install(parser.parse_args(), base, xdg)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'Kurulum tamamlanmadı: {exc}\n')


if __name__ == '__main__':
    main()
