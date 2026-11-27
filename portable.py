"""Taşınabilir klasörden sistem kurulumu olmadan başlat."""
import os
from pathlib import Path
import sys


def main():
    if getattr(sys, 'frozen', False):
        bundle = Path(sys.executable).resolve().parent
    else:
        entry = Path(__file__).resolve().parent
        bundle = entry.parent if entry.name == 'app' else entry
    if os.name == 'nt':
        runtime = bundle / 'runtime'
        os.environ['PATH'] = str(runtime / 'bin') + os.pathsep + os.environ.get('PATH', '')
        os.environ['GI_TYPELIB_PATH'] = str(runtime / 'lib' / 'girepository-1.0')
        os.environ['GSETTINGS_SCHEMA_DIR'] = str(runtime / 'share' / 'glib-2.0' / 'schemas')
        os.environ['XDG_DATA_DIRS'] = str(runtime / 'share')
        gtk_dlls = os.add_dll_directory(str(runtime / 'bin'))
    else:
        gtk_dlls = None
    os.environ.setdefault('GSETTINGS_BACKEND', 'memory')
    try:
        from desktop import main as run
        return run(default_runtime=bundle / 'motor')
    except Exception as exc:
        if os.name != 'nt':
            raise
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, f'Uygulama açılamadı / Could not start:\n{exc}', 'amdl Masaüstü', 16)
        return 1
    finally:
        if gtk_dlls is not None:
            gtk_dlls.close()


if __name__ == '__main__':
    raise SystemExit(main())
