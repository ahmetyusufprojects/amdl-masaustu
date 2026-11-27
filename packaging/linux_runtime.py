"""Ubuntu 24.04 (glibc 2.39) tabanlı x86_64 Linux tek klasör derlemesi."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.request import urlopen


_SOURCE = Path(__file__).resolve().parent.parent
_NAME = "amdl-masaustu"
_BASE = "ubuntu-base-24.04.5-base-amd64.tar.gz"
_BASE_URL = "https://cdimage.ubuntu.com/ubuntu-base/releases/24.04/release/" + _BASE
# Ubuntu'nun aynı dizindeki SHA256SUMS dosyasından.
_BASE_SHA256 = "e77b6f10c2590cef872b33ee9f635a0e3fd1f57fb074c0e52b5c7f56147a0c86"
_REQUIREMENTS = "linux-requirements.txt"

# bwrap'ın tek kimlik eşlemesinde dpkg bakım betikleri (dbus/fontconfig vb.)
# sistem kullanıcılarına chown yapamaz. APT ile imzalı paketleri çözüp yalnızca
# dosyalarını açıyoruz; gerekli önbellekleri servis başlatmadan oluşturuyoruz.
_PROVISION = r'''
set -o pipefail
apt=(apt-get -o APT::Sandbox::User=root -o Acquire::Retries=3)
"${apt[@]}" -o APT::Update::Error-Mode=any update
"${apt[@]}" --download-only install -y --no-install-recommends \
    ca-certificates binutils libpython3.12t64 python3-venv python3-gi python3-gi-cairo python3-yaml \
    gir1.2-gtk-4.0 libglib2.0-bin librsvg2-common shared-mime-info adwaita-icon-theme hicolor-icon-theme
for deb in /var/cache/apt/archives/*.deb; do
    dpkg-deb --fsys-tarfile "$deb" | tar --no-same-owner --no-same-permissions -xf - -C /
done
ldconfig
find /usr/share/ca-certificates -name '*.crt' -printf '%P\n' | sort > /etc/ca-certificates.conf
update-ca-certificates --hooksdir /nonexistent
glib-compile-schemas /usr/share/glib-2.0/schemas
update-mime-database /usr/share/mime
python3 -I -m venv --system-site-packages /venv
/venv/bin/python -I -m pip --isolated install --disable-pip-version-check \
    --only-binary=:all: --require-hashes -r /linux-requirements.txt
'''

# GLib kancası sistem XDG dizinlerini kaybetmesin (örn. dosya yöneticisi).
# Yeni sistem temalarının CSS'i paketteki GTK sürümüyle uyumsuz olabilir.
_RUNTIME_HOOK = '''
import os

if not os.environ.get("XDG_DATA_DIRS"):
    os.environ["XDG_DATA_DIRS"] = "/usr/local/share:/usr/share"
os.environ.setdefault("GTK_THEME", "Adwaita")
'''

_SPEC = '''
a = Analysis(
    ["/src/portable.py"],
    pathex=["/src"],
    datas=[
        ("/src/icon.svg", "."),
        ("/work/io.github.AmdlMasaustu.svg", "share/icons/hicolor/scalable/apps"),
    ],
    hooksconfig={"gi": {
        "module-versions": {"Gtk": "4.0", "Gdk": "4.0"},
        "icons": ["Adwaita", "hicolor"],
    }},
    runtime_hooks=["/work/xdg.py"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="amdl-masaustu", upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="amdl-masaustu", upx=False)
'''


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _base_archive(cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / _BASE
    if archive.is_file() and _checksum(archive) == _BASE_SHA256:
        return archive
    with tempfile.TemporaryDirectory(prefix="download-", dir=cache) as directory:
        incoming = Path(directory) / _BASE
        with urlopen(_BASE_URL, timeout=60) as response, incoming.open("xb") as file:
            if not response.geturl().startswith("https://"):
                raise ValueError("Ubuntu Base indirmesi HTTPS dışına yönlendirildi")
            shutil.copyfileobj(response, file)
        if _checksum(incoming) != _BASE_SHA256:
            raise ValueError(f"Ubuntu Base SHA-256 uyuşmuyor: {_BASE}")
        incoming.replace(archive)
    return archive


def _sandbox(bwrap: str, root: Path) -> list[str]:
    return [
        bwrap, "--unshare-user", "--uid", "0", "--gid", "0",
        "--unshare-pid", "--unshare-ipc", "--unshare-uts", "--die-with-parent",
        "--bind", str(root), "/", "--dev", "/dev", "--proc", "/proc",
        "--tmpfs", "/run", "--tmpfs", "/tmp", "--clearenv",
        "--setenv", "PATH", "/usr/sbin:/usr/bin:/sbin:/bin",
        "--setenv", "HOME", "/root", "--setenv", "LC_ALL", "C.UTF-8",
    ]


def _validate(bundle: Path) -> None:
    with (bundle / _NAME).open("rb") as executable:
        elf = executable.read(20)
    if elf[:6] != b"\x7fELF\x02\x01" or elf[18:20] != b"\x3e\x00":
        raise ValueError("Linux başlatıcısı x86_64 ELF değil")
    for name in (
        "libgtk-4.so.1", "gi_typelibs/Gtk-4.0.typelib", "gi_typelibs/Gdk-4.0.typelib",
        "lib/gdk-pixbuf/loaders/libpixbufloader-svg.so", "lib/gdk-pixbuf/loaders.cache",
        "share/glib-2.0/schemas/gschemas.compiled",
        "icon.svg", "share/icons/hicolor/scalable/apps/io.github.AmdlMasaustu.svg",
    ):
        if not (bundle / "_internal" / name).is_file():
            raise FileNotFoundError(f"Linux paketinde eksik dosya: _internal/{name}")


def build_runtime(destination: Path, cache: Path) -> None:
    """`amdl-masaustu` ve `_internal/` üretir; var olan çıktıları değiştirmez.

    Derleme Linux x86_64, GNU tar, ağ erişimi ve kullanıcı ad alanı açabilen
    bwrap gerektirir. `cache/ubuntu-base/` yalnızca doğrulanmış baz arşivi tutar.
    Çıktı GTK4 ve Python'u taşır; glibc ve grafik altyapısı (XCB, Wayland,
    sürücüler ve yazı tipleri) hedef masaüstünden kullanılır.
    """
    if (os.uname().sysname, os.uname().machine) != ("Linux", "x86_64"):
        raise RuntimeError("Ubuntu Base derlemesi Linux x86_64 gerektirir")
    bwrap, tar = shutil.which("bwrap"), shutil.which("tar")
    if not bwrap or not tar:
        raise RuntimeError("Linux paketi oluşturmak için bwrap ve GNU tar gerekli")
    if not (_SOURCE / "portable.py").is_file():
        raise FileNotFoundError(_SOURCE / "portable.py")
    destination, cache = destination.resolve(), cache.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    final_exe, final_internal = destination / _NAME, destination / "_internal"
    for path in (final_exe, final_internal):
        if path.exists() or path.is_symlink():
            raise FileExistsError(path)

    with tempfile.TemporaryDirectory(prefix="amdl-linux-") as scratch, \
            tempfile.TemporaryDirectory(prefix=".linux-stage-", dir=destination) as staged:
        root, work = Path(scratch) / "root", Path(scratch) / "work"
        root.mkdir()
        work.mkdir()
        archive = _base_archive(cache / "ubuntu-base")
        subprocess.run(
            [tar, "--no-same-owner", "--no-same-permissions", "-xzf", str(archive), "-C", str(root)],
            cwd=_SOURCE, check=True,
        )
        sandbox = _sandbox(bwrap, root)
        subprocess.run(
            [*sandbox, "--ro-bind", "/etc/resolv.conf", "/etc/resolv.conf",
             "--ro-bind", str(_SOURCE / "packaging" / _REQUIREMENTS), "/linux-requirements.txt",
             "--chdir", "/tmp", "--", "/bin/bash", "-ec", _PROVISION],
            cwd=_SOURCE, check=True,
        )
        shutil.copyfile(_SOURCE / "icon.svg", work / "io.github.AmdlMasaustu.svg")
        (work / "xdg.py").write_text(_RUNTIME_HOOK, encoding="utf-8")
        (work / "linux.spec").write_text(_SPEC, encoding="utf-8")
        subprocess.run(
            [*sandbox, "--unshare-net", "--ro-bind", str(_SOURCE), "/src",
             "--ro-bind", str(work), "/work", "--bind", staged, "/out", "--chdir", "/src",
             "--", "/venv/bin/python", "-I", "-m", "PyInstaller", "--noconfirm",
             "--distpath", "/out", "--workpath", "/tmp/build", "/work/linux.spec"],
            cwd=_SOURCE, check=True,
        )
        bundle = Path(staged) / _NAME
        _validate(bundle)
        (bundle / "_internal").rename(final_internal)
        try:
            (bundle / _NAME).rename(final_exe)
        except OSError:
            final_internal.rename(bundle / "_internal")
            raise
