"""Yerel motor bağlantısı ve süreç yardımcıları."""
from contextlib import contextmanager
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

import yaml

LOCAL = 'http://127.0.0.1:12340'
WINDOWS = os.name == 'nt'
LOGIN_READY = b'AMDL_LOGIN_READY'
LOGIN_INIT = b'''#!/bin/busybox sh
/bin/busybox mv /system/bin/lite /system/bin/lite-original || exit 1
/bin/busybox mv /amdl-login-shim /system/bin/lite || exit 1
exec /init
'''
LOGIN_SHIM = b'''#!/bin/busybox sh
umask 077
exec </dev/ttyS0 >/dev/ttyS0 2>&1
/bin/busybox stty -echo 2>/dev/null
printf 'AMDL_LOGIN_READY\\n'
if IFS= read -r count; then
    case "$count" in
      [1-8])
        while [ "$count" -gt 0 ]; do
          IFS= read -r line || break
          printf '%s\\n' "$line"
          count=$((count-1))
        done >/amdl-login.args
        unset line
        if [ "$count" -eq 0 ]; then
          LITE_ARGS_FILE=/amdl-login.args /system/bin/lite-original
        fi
        ;;
    esac
fi
/bin/busybox rm -f /amdl-login.args
/bin/busybox poweroff -f
'''

ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
SUMMARY = re.compile(r'Completed:\s*(\d+)/(\d+).*?Errors:\s*(\d+)')
PERCENT = re.compile(r'(?<!\d)(\d{1,3})\s*%')


def read_yaml(path):
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError('config.yaml')
    return data


def write_yaml(path, data):
    fd, name = tempfile.mkstemp(prefix='.amdl-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def is_link(value):
    try:
        u = urllib.parse.urlsplit(value)
        return (u.scheme == 'https' and u.netloc == 'music.apple.com' and
                u.path not in ('', '/') and not any(c.isspace() for c in value))
    except ValueError:
        return False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def status(endpoint):
    try:
        u = urllib.parse.urlsplit(endpoint)
        if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.query or u.fragment:
            return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(endpoint.rstrip('/') + '/status', timeout=1.5) as f:
            data = json.loads(f.read(65536))
        regions = data['data']['regions']
        return regions if data['code'] == 0 and isinstance(regions, list) else None
    except urllib.error.HTTPError as exc:
        exc.close()
        return None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def cancel(proc, tree=False):
    if proc and proc.poll() is None:
        try:
            if WINDOWS:
                if tree:
                    taskkill = Path(os.environ['SystemRoot']) / 'System32' / 'taskkill.exe'
                    subprocess.run([str(taskkill), '/T', '/F', '/PID', str(proc.pid)],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   timeout=3, **process_options())
                if proc.poll() is None:
                    proc.terminate()
            else:
                os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except (OSError, subprocess.TimeoutExpired):
            if proc.poll() is None:
                proc.terminate()


def process_options():
    return {'creationflags': subprocess.CREATE_NO_WINDOW} if WINDOWS else {'start_new_session': True}


def child_env(runtime=None):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith('CLIPROXY_') or key in ('GH_TOKEN', 'GITHUB_TOKEN'):
            env.pop(key)
    if not WINDOWS and getattr(sys, 'frozen', False):
        original = env.pop('LD_LIBRARY_PATH_ORIG', None)
        if original is None:
            env.pop('LD_LIBRARY_PATH', None)
        else:
            env['LD_LIBRARY_PATH'] = original
    if runtime is not None and (runtime / 'bin').is_dir():
        env['PATH'] = str(runtime / 'bin') + os.pathsep + env.get('PATH', '')
    return env


def binary(runtime, name):
    return runtime / (name + ('.exe' if WINDOWS else ''))


def lock_runtime(runtime):
    lock = (runtime / 'wrapper-lite' / '.oturum.lock').open('a+b')
    try:
        if WINDOWS:
            import msvcrt
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        raise
    return lock


def cpio_overlay(files):
    image = bytearray()
    for ino, (name, contents) in enumerate([*files.items(), ('TRAILER!!!', b'')], 1):
        encoded = name.encode('ascii') + b'\0'
        fields = (ino, 0o100755 if contents else 0, 0, 0, 1, 0, len(contents), 0, 0, 0, 0, len(encoded), 0)
        image.extend(b'070701' + ''.join(f'{value:08x}' for value in fields).encode('ascii'))
        image.extend(encoded)
        image.extend(b'\0' * (-len(image) % 4))
        image.extend(contents)
        image.extend(b'\0' * (-len(image) % 4))
    return gzip.compress(bytes(image), mtime=0)


def qemu_home(runtime):
    return runtime / 'wrapper-lite' / 'qemu'


def qemu_command(runtime, initrd):
    q = qemu_home(runtime)
    env = child_env(runtime)
    if not WINDOWS:
        env['LD_LIBRARY_PATH'] = str(q / 'lib')
    env['QEMU_MODULE_DIR'] = str(q / 'bin')
    kvm = not WINDOWS and os.access('/dev/kvm', os.R_OK | os.W_OK)
    console = 'console=ttyS0 quiet net.ifnames=0 biosdevname=0 rdinit=/amdl-login-init'
    block = json.dumps({'driver': 'raw', 'node-name': 'amdl_disk',
                        'file': {'driver': 'file', 'filename': str(q / 'data.img')}}, ensure_ascii=False)
    cmd = [str(binary(q / 'bin', 'qemu-system-x86_64')), '-L', str(q / 'bin'),
           '-accel', 'kvm' if kvm else 'tcg', '-cpu', 'host' if kvm else 'max',
           '-m', '512', '-smp', '2', '-kernel', str(q / 'vmlinuz-lite-qemu'),
           '-initrd', str(initrd), '-append', console, '-display', 'none', '-monitor', 'none',
           '-serial', 'stdio', '-no-reboot', '-nic', 'user,model=e1000',
           '-blockdev', block, '-device', 'virtio-blk-pci,drive=amdl_disk']
    return cmd, env


def service_command(runtime, port):
    return [str(binary(runtime / 'wrapper-lite', 'wrapper-lite-qemu')),
            '--host', '127.0.0.1', '--host-port', str(int(port)), '--guest-port', '12340']


def start_service(runtime, port, lock):
    inherit = {} if WINDOWS else {'pass_fds': (lock.fileno(),)}
    return subprocess.Popen(service_command(runtime, port), cwd=runtime, env=child_env(runtime),
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            **process_options(), **inherit)


def login_payload(email, password):
    if not email or not password or ':' in email:
        raise ValueError('credentials')
    return guest_payload(['--login', f'{email}:{password}', '--base-dir', '/data'])


def guest_payload(args):
    if not 1 <= len(args) <= 8 or any(ord(c) < 32 or ord(c) == 127 for arg in args for c in arg):
        raise ValueError('credentials')
    payload = ('\n'.join([str(len(args)), *args]) + '\n').encode()
    if len(payload) > 3000:
        raise ValueError('credentials')
    return payload


@contextmanager
def login_process(runtime):
    with tempfile.TemporaryDirectory(prefix='amdl-login-') as temp:
        initrd = Path(temp) / 'login.cpio.gz'
        with (qemu_home(runtime) / 'lite-initramfs.cpio.gz').open('rb') as original, initrd.open('wb') as dst:
            shutil.copyfileobj(original, dst)
            dst.write(cpio_overlay({'amdl-login-init': LOGIN_INIT, 'amdl-login-shim': LOGIN_SHIM}))
        cmd, env = qemu_command(runtime, initrd)
        with subprocess.Popen(cmd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, **process_options()) as proc:
            try:
                yield proc
            finally:
                cancel(proc)
