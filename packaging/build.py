#!/usr/bin/env python3
"""Windows ve Linux x64 taşınabilir klasörlerini temiz kaynaklardan üret."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

AMDL_RELEASE = 'https://github.com/zhaarey/apple-music-downloader/releases/download/v0.1.4/'
WRAPPER_API = 'repos/WorldObservationLog/wrapper/actions/artifacts/'
FFMPEG_RELEASE = ('https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/'
                  'autobuild-2026-11-22-12-36/ffmpeg-n8.1.3-39-g660b5aa7db-')
SOURCES = {
    'linux': (
        (AMDL_RELEASE + 'amdl_linux_amd64', '1a3a4000edd74be98efccf7f611b97d47ef822d8e059805c6aaaef98f0477747'),
        (WRAPPER_API + '13565793609/zip', 'efa69efab16b188ff486f26e9278c94938f9cecc3dd15e3e8c11b5270fa54d04'),
        (FFMPEG_RELEASE + 'linux64-gpl-8.1.tar.xz', 'b1c6934b4c3cbbbc0e0a39671c012437db99b719d8ec640ba3371a5876115d78'),
    ),
    'windows': (
        (AMDL_RELEASE + 'amdl_windows_amd64.exe', '952b379dbeb72245c48e77581dea6f4ad74a6d0f463000f32ec5ba17a5b42eec'),
        (WRAPPER_API + '13565524179/zip', '3a7ace6760df25f57f34d2e58cf522bfe86e318ffb88eed23127efbac6b19170'),
        (FFMPEG_RELEASE + 'win64-gpl-8.1.zip', 'b16431997ec2685c1baab7dc214537cdbdd48dabdd6e233d4ab0f1e316de0dc7'),
    ),
}


def hash_file(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def fetch(cache, asset):
    address, digest = asset
    target = cache / digest
    if target.is_file() and hash_file(target) == digest:
        return target
    with tempfile.TemporaryDirectory(prefix='asset-', dir=cache) as tmp:
        incoming = Path(tmp) / 'download'
        if address.startswith('https://'):
            subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location', '--retry', '2',
                            '--max-time', '360', '--output', str(incoming), address], check=True)
        else:
            with incoming.open('wb') as stream:
                subprocess.run(['gh', 'api', address], stdout=stream, check=True)
        if hash_file(incoming) != digest:
            raise ValueError(f'SHA-256 eşleşmedi: {address}')
        incoming.replace(target)
    return target


def prefetch(cache, platforms):
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    assets = {asset for platform in platforms for asset in SOURCES[platform]}
    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(zip(assets, pool.map(lambda asset: fetch(cache, asset), assets)))


def _zip_path(info):
    p = PurePosixPath(info.filename)
    mode = info.external_attr >> 16
    if (not p.parts or p.is_absolute() or '..' in p.parts or '\\' in info.filename or
            any(':' in part for part in p.parts) or stat.S_ISLNK(mode)):
        raise ValueError('Güvenli olmayan ZIP girdisi.')
    return p


def unpack_wrapper(archive, target, windows):
    with tempfile.TemporaryDirectory(prefix='wrapper-') as scratch, zipfile.ZipFile(archive) as zip_:
        extracted = Path(scratch) / 'wrapper-lite'
        extracted.mkdir()
        seen = set()
        for info in zip_.infolist():
            path = _zip_path(info)
            key = str(path).casefold() if windows else str(path)
            if key in seen:
                raise ValueError('Wrapper paketinde yinelenen dosya yolu.')
            seen.add(key)
            original = extracted.joinpath(*path.parts)
            if info.is_dir():
                original.mkdir(parents=True, exist_ok=True)
            else:
                original.parent.mkdir(parents=True, exist_ok=True)
                with zip_.open(info) as src, original.open('xb') as dst:
                    shutil.copyfileobj(src, dst)
        suffix = '.exe' if windows else ''
        for rel in (f'wrapper-lite-qemu{suffix}', f'qemu/bin/qemu-system-x86_64{suffix}'):
            path = extracted / rel
            if not path.is_file():
                raise ValueError(f'Wrapper çalıştırılabilir dosyası bulunamadı: {rel}')
            path.chmod(0o755)
        from engine import missing_login_component

        missing = missing_login_component(extracted.parent, windows)
        if missing:
            raise ValueError(f'Wrapper giriş bileşeni eksik: {missing}')
        (extracted / 'qemu/data.img').chmod(0o600)
        shutil.copytree(extracted, target)


def write_ffmpeg(archive, target, licenses, windows):
    ff = target / ('ffmpeg.exe' if windows else 'ffmpeg')
    target.mkdir()
    licenses.mkdir(exist_ok=True)
    if windows:
        with zipfile.ZipFile(archive) as zip_:
            infos = [i for i in zip_.infolist()
                     if _zip_path(i).parts[-2:] == ('bin', ff.name)]
            if len(infos) != 1:
                raise ValueError('Windows FFmpeg çalıştırılabilir dosyası bulunamadı.')
            with zip_.open(infos[0]) as src, ff.open('xb') as dst:
                shutil.copyfileobj(src, dst)
            for info in zip_.infolist():
                name = _zip_path(info).name
                if name in ('LICENSE.txt', 'LICENSE', 'COPYING.GPLv3'):
                    (licenses / f'ffmpeg-{name}').write_bytes(zip_.read(info))
    else:
        with tarfile.open(archive, 'r|xz') as tar:
            for info in tar:
                names = PurePosixPath(info.name).parts
                if not names or not info.isfile():
                    continue
                if names[-2:] == ('bin', ff.name):
                    with closing(tar.extractfile(info)) as src, ff.open('xb') as dst:
                        shutil.copyfileobj(src, dst)
                elif names[-1] in ('LICENSE.txt', 'LICENSE', 'COPYING.GPLv3'):
                    with closing(tar.extractfile(info)) as src:
                        (licenses / f'ffmpeg-{names[-1]}').write_bytes(src.read())
    ff.chmod(0o755)


def prepare_motor(stage, platform, assets):
    from engine import write_yaml
    from settings import FIELDS, put

    windows = platform == 'windows'
    motor = stage / 'motor'
    motor.mkdir(mode=0o700)
    amdl, wrapper, ffmpeg = (assets[asset] for asset in SOURCES[platform])
    binary = motor / ('amdl.exe' if windows else 'amdl')
    shutil.copyfile(amdl, binary)
    binary.chmod(0o755)
    unpack_wrapper(wrapper, motor / 'wrapper-lite', windows)
    write_ffmpeg(ffmpeg, motor / 'bin', stage / 'lisanslar', windows)
    defaults = {}
    for key, value, *_ in FIELDS:
        put(defaults, key, value)
    write_yaml(motor / 'config.yaml', defaults)
    origins = ['Bu paket, üçüncü taraf motorlarının sabitlenmiş kopyalarını içerir.',
               'The package includes pinned third-party components.',
               'https://github.com/zhaarey/apple-music-downloader',
               'https://github.com/WorldObservationLog/wrapper/tree/lite',
               'https://github.com/FFmpeg-Builds/FFmpeg-Builds',
               'https://github.com/FFmpeg/FFmpeg/tree/660b5aa7db', '']
    for address, hash_ in SOURCES[platform]:
        origins.append(f'{hash_}  {address}')
    (stage / 'lisanslar' / 'KAYNAKLAR.txt').write_text('\n'.join(origins) + '\n', encoding='utf-8')


def write_archive(folder, path):
    if path.suffix == '.zip':
        with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
            for entry in sorted(folder.rglob('*')):
                if entry.is_file():
                    archive.write(entry, f'{folder.name}/{entry.relative_to(folder).as_posix()}')
    else:
        def portable_owner(member):
            member.uid = member.gid = 0
            member.uname = member.gname = 'root'
            return member

        with tarfile.open(path, 'w:gz', compresslevel=3) as archive:
            archive.add(folder, arcname=folder.name, filter=portable_owner)


def build(platform, output, cache, assets):
    name = f'amdl-Masaustu-{platform}-x64'
    folder = output / name
    archive = output / (name + ('.zip' if platform == 'windows' else '.tar.gz'))
    if folder.exists() or archive.exists():
        raise ValueError(f'Çıktı zaten var; üzerine yazılmadı: {name}')
    with tempfile.TemporaryDirectory(prefix='bundle-', dir=output) as tmp:
        stage = Path(tmp) / name
        stage.mkdir()
        if platform == 'windows':
            from windows_runtime import build_runtime
            app = stage / 'app'
            app.mkdir()
            for name_ in ('portable.py', 'desktop.py', 'engine.py', 'settings.py', 'icon.svg'):
                shutil.copyfile(ROOT / name_, app / name_)
        else:
            from linux_runtime import build_runtime
        build_runtime(stage, cache)
        prepare_motor(stage, platform, assets)
        shutil.copyfile(ROOT / 'packaging' / 'AC-BENI.txt', stage / 'AC-BENI.txt')
        packed = Path(tmp) / archive.name
        write_archive(stage, packed)
        digest = hash_file(packed)
        stage.rename(folder)
        packed.rename(archive)
        (output / (archive.name + '.sha256')).write_text(f'{digest}  {archive.name}\n', encoding='ascii')
    print(archive, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('platform', choices=('linux', 'windows', 'all'))
    parser.add_argument('--out', type=Path, default=ROOT / 'dist')
    parser.add_argument('--cache', type=Path, default=Path.home() / '.cache/amdl-masaustu/paketleme')
    parser.add_argument('--prefetch-only', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    platforms = ('linux', 'windows') if args.platform == 'all' else (args.platform,)
    cache, output = args.cache.resolve(), args.out.resolve()
    assets = prefetch(cache, platforms)
    if not args.prefetch_only:
        output.mkdir(parents=True, exist_ok=True)
        for platform in platforms:
            build(platform, output, cache, assets)


if __name__ == '__main__':
    main()
