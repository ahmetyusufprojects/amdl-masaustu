"""Linux x86_64 üzerinde taşınabilir Windows x64 GTK4 çalışma ortamı üretir."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tarfile
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


_REPO = "https://repo.msys2.org/mingw/ucrt64/"
_PREFIX = "mingw-w64-ucrt-x86_64-"
_ROOT_PACKAGES = ("python", "python-gobject", "python-yaml", "gtk4", "librsvg", "shared-mime-info")
_LLVM_TAG = "20251118"
_LLVM_DIR = f"llvm-mingw-{_LLVM_TAG}-ucrt-ubuntu-22.04-x86_64"
_LLVM_FILE = _LLVM_DIR + ".tar.xz"
_LLVM_URL = f"https://github.com/mstorsjo/llvm-mingw/releases/download/{_LLVM_TAG}/{_LLVM_FILE}"
# mstorsjo/llvm-mingw sürüm varlığının yayımlanmış SHA-256 özeti (318346946).
_LLVM_HASH = "53a0c22caa46b501e1c089e1c31b24a7c0e0d5a86f8ad12b131aafd4cee01ef4"
_DEP = re.compile(r"([a-zA-Z0-9@._+-]+)(?:(<=|>=|=|<|>)([^\s<>=]+))?")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_PIXBUF = Path("lib/gdk-pixbuf-2.0/2.10.0")


@dataclass(frozen=True)
class _Package:
    name: str
    version: str
    filename: str
    sha256: str
    deps: tuple[str, ...]
    provides: tuple[str, ...]


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, path: Path, sha256: str | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if sha256 is not None and path.is_file() and _hash(path) == sha256:
        return path
    for attempt in range(3):
        try:
            # Paralel yapılar bitmemiş bir indirmeyi önbellekte görmez.
            with tempfile.TemporaryDirectory(prefix="download-", dir=path.parent) as work:
                incoming = Path(work) / path.name
                with urlopen(url, timeout=60) as response, incoming.open("xb") as output:
                    if not response.geturl().startswith("https://"):
                        raise ValueError("HTTPS olmayan indirme yönlendirmesi")
                    shutil.copyfileobj(response, output)
                if sha256 is not None and _hash(incoming) != sha256:
                    raise ValueError(f"SHA-256 uyuşmuyor: {path.name}")
                incoming.replace(path)
            return path
        except (URLError, TimeoutError, ConnectionError) as error:
            if attempt == 2 or (isinstance(error, HTTPError) and error.code not in (429, 500, 502, 503, 504)):
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("indirme döngüsü")


@contextmanager
def _zstd_tar(path: Path, zstd: str):
    # Yalnızca tar verisi okunur; arşivdeki kanca ve betikler çalıştırılmaz.
    with subprocess.Popen([zstd, "-dc", "--", str(path)], stdout=subprocess.PIPE) as proc:
        assert proc.stdout is not None
        try:
            with tarfile.open(fileobj=proc.stdout, mode="r|") as archive:
                yield archive
            while proc.stdout.read(1024 * 1024):
                pass
            if proc.wait() != 0:
                raise ValueError(f"Zstandard arşivi açılamadı: {path.name}")
        except BaseException:
            proc.kill()
            raise


def _database(path: Path, zstd: str) -> dict[str, _Package]:
    packages = {}
    with _zstd_tar(path, zstd) as entries:
        for member in entries:
            if not member.isfile() or not member.name.endswith("/desc"):
                continue
            if member.size > 1024 * 1024:
                raise ValueError("Çok büyük MSYS2 paket kaydı")
            fields = {}
            assert (file := entries.extractfile(member)) is not None
            with file:
                for block in file.read().decode("utf-8").strip().split("\n\n"):
                    tag, *values = block.splitlines()
                    fields[tag] = tuple(values)
            name, = fields["%NAME%"]
            if not name.startswith(_PREFIX):
                continue
            version, = fields["%VERSION%"]
            filename, = fields["%FILENAME%"]
            sha256, = fields["%SHA256SUM%"]
            if (not re.fullmatch(r"[a-zA-Z0-9@._+~\-]+\.pkg\.tar\.zst", filename)
                    or not filename.startswith(name + "-") or not _SHA256.fullmatch(sha256)
                    or name in packages or not _DEP.fullmatch(name)):
                raise ValueError(f"Geçersiz MSYS2 paket kaydı: {name!r}")
            packages[name] = _Package(name, version, filename, sha256,
                                      fields.get("%DEPENDS%", ()), fields.get("%PROVIDES%", ()))
    return packages


def _dependency(spec: str) -> tuple[str, str | None, str | None]:
    match = _DEP.fullmatch(spec)
    if not match:
        raise ValueError(f"Geçersiz MSYS2 bağımlılığı: {spec!r}")
    return match.groups()


def _version_ok(actual: str | None, op: str | None, required: str | None) -> bool:
    if op is None:
        return True
    if actual is None:
        return False
    assert required is not None

    def split(version):
        epoch, sep, rest = version.partition(":")
        release = (rest if sep else epoch).split("-", 1)
        return int(epoch) if sep else 0, release[0], release[1] if len(release) == 2 else ""

    ae, av, ar = split(actual)
    be, bv, br = split(required)
    if not ar or not br:
        ar = br = ""
    if (ae, av, ar) == (be, bv, br):
        return op in ("=", "<=", ">=")
    # Depodaki sıralamalı kısıtlar sayısaldır. Yeni bir biçim gelirse yanlış
    # ABI seçmektense hata ver; Arch'ın tüm vercmp kurallarını taklit etme.
    def numeric(value):
        if not value:
            return ()
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", value):
            raise ValueError(f"Desteklenmeyen MSYS2 sürüm karşılaştırması: {actual!r}, {required!r}")
        return tuple(map(int, value.split(".")))

    a, b = (ae, numeric(av), numeric(ar)), (be, numeric(bv), numeric(br))
    return {"=": a == b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]


def _closure(packages: dict[str, _Package]) -> list[_Package]:
    providers: dict[str, list[tuple[_Package, str | None]]] = {}
    for package in packages.values():
        for entry in package.provides:
            name, _, version = _dependency(entry)
            providers.setdefault(name, []).append((package, version))
    selected: dict[str, _Package] = {}
    todo = [_PREFIX + name for name in _ROOT_PACKAGES]
    while todo:
        spec = todo.pop()
        name, op, version = _dependency(spec)
        direct = packages.get(name)
        if direct and _version_ok(direct.version, op, version):
            package = direct
        else:
            valid = {p.name: p for p, v in providers.get(name, ()) if _version_ok(v, op, version)}
            installed = valid.keys() & selected.keys()
            candidates = installed or valid.keys()
            if len(candidates) != 1:
                raise ValueError(f"MSYS2 bağımlılığı için tek sağlayıcı bulunamadı: {spec} ({sorted(candidates)})")
            package = valid[next(iter(candidates))]
        if package.name not in selected:
            selected[package.name] = package
            todo.extend(package.deps)
    return sorted(selected.values(), key=lambda p: p.name)


def _parts(name: str) -> tuple[str, ...]:
    if name.startswith("/") or "\\" in name or "\0" in name:
        raise ValueError(f"Güvensiz arşiv yolu: {name!r}")
    parts = tuple(part for part in name.split("/") if part not in ("", "."))
    if ".." in parts:
        raise ValueError(f"Güvensiz arşiv yolu: {name!r}")
    return parts


def _keep(parts: tuple[str, ...]) -> bool:
    if len(parts) < 2 or parts[0] not in ("bin", "etc", "lib", "share", "ssl"):
        return False
    if parts[0] == "bin" and not parts[-1].lower().endswith((".exe", ".dll")):
        return False
    return (parts[:2] not in (("lib", "pkgconfig"), ("lib", "cmake"), ("share", "pkgconfig"),
                             ("share", "gir-1.0"), ("share", "man"), ("share", "cmake"),
                             ("share", "info"), ("share", "aclocal"), ("share", "gtk-doc"))
            and not parts[-1].lower().endswith((".a", ".la", ".pc", ".pyc", ".pyo", ".h"))
            and "__pycache__" not in parts)


def _windows_parts(parts: tuple[str, ...]) -> None:
    for part in parts:
        if (re.search(r'[\x00-\x1f<>:"|?*]', part) or part.endswith((".", " "))
                or re.fullmatch(r"(?i:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])", part.split(".", 1)[0])):
            raise ValueError(f"Geçersiz Windows yolu: {'/'.join(parts)!r}")


def _link_target(member: tarfile.TarInfo, rel: tuple[str, ...]) -> tuple[str, ...]:
    if member.islnk():
        top, *parts = _parts(member.linkname)
        if top != "ucrt64":
            raise ValueError(f"Paket öneki dışına bağlantı: {member.name}")
        return tuple(parts)
    if member.linkname.startswith("/") or "\\" in member.linkname:
        raise ValueError(f"Mutlak sembolik bağlantı: {member.name}")
    target = list(rel[:-1])
    for component in member.linkname.split("/"):
        if component == "..":
            if not target:
                raise ValueError(f"Paket öneki dışına bağlantı: {member.name}")
            target.pop()
        elif component not in ("", "."):
            target.append(component)
    return tuple(target)


def _extract_packages(archives: list[Path], runtime: Path, zstd: str) -> None:
    links: dict[tuple[str, ...], tuple[str, ...]] = {}
    seen: dict[str, tuple[str, ...]] = {}
    for path in archives:
        with _zstd_tar(path, zstd) as archive:
            for member in archive:
                parts = _parts(member.name)
                if not parts or parts[0] != "ucrt64" or member.isdir():
                    continue
                rel = parts[1:]
                if not _keep(rel):
                    continue
                _windows_parts(rel)
                # Büyük/küçük harf farkıyla aynı Windows yoluna yazılmasın.
                for i in range(1, len(rel) + 1):
                    prefix = rel[:i]
                    if seen.setdefault("/".join(prefix).casefold(), prefix) != prefix:
                        raise ValueError(f"Çakışan Windows yolu: {member.name}")
                dest = runtime.joinpath(*rel)
                if dest.exists() or rel in links:
                    raise ValueError(f"Çakışan paket dosyası: {member.name}")
                if member.issym() or member.islnk():
                    target = _link_target(member, rel)
                    _windows_parts(target)
                    links[rel] = target
                elif member.isfile():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    assert (file := archive.extractfile(member)) is not None
                    with file, dest.open("xb") as output:
                        shutil.copyfileobj(file, output)
                else:
                    raise ValueError(f"Desteklenmeyen tar girdisi: {member.name}")
    # Python takma adları dahil bağlantıları normal dosyaya dönüştür.
    for rel, at in links.items():
        visited = {rel}
        while at in links and at not in visited:
            visited.add(at)
            at = links[at]
        source, dest = runtime.joinpath(*at), runtime.joinpath(*rel)
        if at in visited or not source.is_file():
            raise ValueError(f"Paket bağlantısının hedefi yok veya dosya değil: {dest.relative_to(runtime)} -> {at}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as file, dest.open("xb") as output:
            shutil.copyfileobj(file, output)


# gdk-pixbuf ve librsvg fill_info kayıtları. GdkPixbuf taşınabilir Windows
# derlemesinde modül yolları önbelleğe değil, DLL'in çalışma önekine göredir.
_PIXBUF_FORMATS = {
    "libpixbufloader-png.dll": r'''"png" 5 "gdk-pixbuf" "PNG" "LGPL"
"image/png" ""
"png" ""
"\211PNG\r\n\032\n" "" 100''',
    "libpixbufloader-jpeg.dll": r'''"jpeg" 5 "gdk-pixbuf" "JPEG" "LGPL"
"image/jpeg" ""
"jpeg" "jpe" "jpg" ""
"\377\330" "" 100''',
    "pixbufloader_svg.dll": r'''"svg" 6 "gdk-pixbuf" "Scalable Vector Graphics" "LGPL"
"image/svg+xml" "image/svg" "image/svg-xml" "image/vnd.adobe.svg+xml" "text/xml-svg" "image/svg+xml-compressed" ""
"svg" "svgz" "svg.gz" ""
" <svg" "*    " 100
" <!DOCTYPE svg" "*             " 100''',
}


def _make_data(runtime: Path, schemas: str, mime: str, scratch: Path) -> None:
    subprocess.run([schemas, "--strict", str(runtime / "share/glib-2.0/schemas")], check=True, cwd=scratch)
    subprocess.run([mime, str(runtime / "share/mime")], check=True, cwd=scratch,
                   env={**os.environ, "XDG_DATA_DIRS": str(runtime / "share")})
    entries = ["# GdkPixbuf Image Loader Modules file\n"]
    for filename, info in _PIXBUF_FORMATS.items():
        rel = _PIXBUF / "loaders" / filename
        if not (runtime / rel).is_file():
            raise FileNotFoundError(f"GdkPixbuf modülü eksik: {rel}")
        entries.append(f'"{rel.as_posix()}"\n{info}\n')
    (runtime / _PIXBUF / "loaders.cache").write_text("\n".join(entries) + "\n", encoding="ascii")


def _check_gui_pe(path: Path) -> None:
    with path.open("rb") as exe:
        dos = exe.read(64)
        if len(dos) == 64 and dos[:2] == b"MZ":
            exe.seek(struct.unpack_from("<I", dos, 60)[0])
            pe = exe.read(94)
            if (len(pe) == 94 and pe[:6] == b"PE\x00\x00\x64\x86"
                    and struct.unpack_from("<H", pe, 24)[0] == 0x20B
                    and struct.unpack_from("<H", pe, 92)[0] == 2):
                return
    raise ValueError(f"Windows x64 GUI PE bekleniyordu: {path.name}")


def _validate_runtime(runtime: Path) -> None:
    for pattern in ("bin/python.exe", "bin/libpython3*.dll", "bin/libgtk-4-1.dll",
                    "bin/libgirepository-*.dll", "lib/girepository-1.0/Gtk-4.0.typelib",
                    "lib/python3.*/encodings/__init__.py", "lib/python3.*/lib-dynload/_ssl*.pyd",
                    "lib/python3.*/site-packages/gi/_gi*.pyd", "lib/python3.*/site-packages/yaml/__init__.py",
                    "share/glib-2.0/schemas/gschemas.compiled", "share/mime/mime.cache"):
        if not any(path.is_file() for path in runtime.glob(pattern)):
            raise FileNotFoundError(f"Çalışma ortamında eksik dosya: {pattern}")

    gui = runtime / "bin/pythonw.exe"
    if not gui.is_file():
        # Sürüm eki olan GUI giriş noktası varsa ana ada kopyala; konsol
        # Python'unu yeniden adlandırmak Windows alt sistemini değiştirmez.
        versioned = sorted(gui.parent.glob("python3.*w.exe")) or sorted(gui.parent.glob("python3w.exe"))
        if len(versioned) != 1:
            raise FileNotFoundError("MSYS2, tanınabilir bir GUI CPython giriş noktası göndermedi")
        _check_gui_pe(versioned[0])
        shutil.copyfile(versioned[0], gui)
    _check_gui_pe(gui)


def _launcher(archive_path: Path, scratch: Path, output: Path) -> None:
    extract = scratch / "toolchain"
    extract.mkdir()
    with tarfile.open(archive_path, "r:xz") as archive:
        def compiler_filter(member, path):
            parts = _parts(member.name)
            if not parts or parts[0] != _LLVM_DIR:
                raise ValueError(f"Beklenmedik llvm-mingw arşiv yolu: {member.name!r}")
            # filter ayrıca izinleri ve bütün sembolik/sabit bağlantı hedeflerini denetler.
            return tarfile.data_filter(member, path)

        archive.extractall(extract, filter=compiler_filter)
    source = Path(__file__).resolve().with_name("windows_launcher.c")
    cc = extract / _LLVM_DIR / "bin/x86_64-w64-mingw32-clang"
    subprocess.run([str(cc), "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-s",
                    "-municode", "-mwindows", str(source), "-lshell32", "-luser32", "-o", str(output)],
                   check=True, cwd=scratch)
    _check_gui_pe(output)


def build_runtime(destination: Path, cache: Path) -> None:
    """`runtime/` ve `amdl-masaustu.exe` üretir; var olan çıktıları değiştirmez.

    Linux x86_64, zstd, glib-compile-schemas ve update-mime-database gerekir.
    Uygulama dosyalarına dokunulmaz; başlatıcı app/portable.py bekler.
    """
    if not hasattr(tarfile, "data_filter"):
        raise RuntimeError("Güvenli tar çıkarımı için güncel Python (tarfile.data_filter) gerekli")
    if os.uname().sysname != "Linux" or os.uname().machine != "x86_64":
        raise RuntimeError("Sabit llvm-mingw dağıtımı Linux x86_64 gerektirir")
    tools = [shutil.which(name) for name in ("zstd", "glib-compile-schemas", "update-mime-database")]
    if not all(tools):
        raise RuntimeError("zstd, glib-compile-schemas ve update-mime-database gerekli")
    zstd, schemas, mime = [str(Path(tool).resolve()) for tool in tools if tool]
    destination, cache = destination.resolve(), cache.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    final_runtime, final_exe = destination / "runtime", destination / "amdl-masaustu.exe"
    for path in (final_runtime, final_exe):
        if path.exists() or path.is_symlink():
            raise FileExistsError(path)

    with tempfile.TemporaryDirectory(prefix="amdl-windows-") as work, \
            tempfile.TemporaryDirectory(prefix=".windows-stage-", dir=destination) as staged:
        scratch, stage = Path(work), Path(staged)
        # HTTPS ile her yapıda güncel resmi DB alınır. Paketler DB'nin SHA-256
        # alanına göre doğrulanır; LLVM ise yukarıdaki sabit özetle doğrulanır.
        db = _download(_REPO + "ucrt64.db", scratch / "index/ucrt64.db")
        packages = _closure(_database(db, zstd))

        def package_archive(package):
            return _download(_REPO + package.filename,
                             cache / "msys2" / package.sha256 / package.filename, package.sha256)

        with ThreadPoolExecutor(max_workers=8) as pool:
            llvm = pool.submit(_download, _LLVM_URL, cache / "llvm-mingw" / _LLVM_HASH / _LLVM_FILE, _LLVM_HASH)
            archives = list(pool.map(package_archive, packages))
            compiler_archive = llvm.result()
        runtime, output = stage / "runtime", stage / final_exe.name
        runtime.mkdir()
        _extract_packages(archives, runtime, zstd)
        _make_data(runtime, schemas, mime, scratch)
        _validate_runtime(runtime)
        _launcher(compiler_archive, scratch, output)
        runtime.rename(final_runtime)
        try:
            output.rename(final_exe)
        except OSError:
            final_runtime.rename(runtime)
            raise
