"""Yerel motor bağlantısı ve süreç yardımcıları."""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request

import yaml

LOCAL = 'http://127.0.0.1:12340'
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


def cancel(proc):
    if proc and proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def child_env():
    env = os.environ.copy()
    for key in list(env):
        if key.startswith('CLIPROXY_') or key == 'GH_TOKEN' or key == 'GITHUB_TOKEN':
            env.pop(key)
    return env


def login_process(runtime, email, password, tty):
    if not email or not password or ':' in email or any(c in email + password for c in '\r\n\0'):
        raise ValueError('credentials')
    return guest_process(runtime, ['--login', f'{email}:{password}', '--base-dir', '/data', '--port', '12340'], tty)


def guest_process(runtime, guest_args, tty):
    q = runtime / 'wrapper-lite' / 'qemu'
    fd = os.memfd_create('local-guest-arguments', os.MFD_CLOEXEC)
    try:
        data = ('\n'.join(guest_args) + '\n').encode()
        with os.fdopen(os.dup(fd), 'wb') as f:
            f.write(data)
        os.lseek(fd, 0, os.SEEK_SET)
        env = child_env()
        env['LD_LIBRARY_PATH'] = str(q / 'lib')
        env['QEMU_MODULE_DIR'] = str(q / 'bin')
        kvm = os.access('/dev/kvm', os.R_OK | os.W_OK)
        cmd = [str(q / 'bin' / 'qemu-system-x86_64'), '-L', str(q / 'bin'),
               '-accel', 'kvm' if kvm else 'tcg', '-cpu', 'host' if kvm else 'max',
               '-m', '512', '-smp', '2', '-kernel', str(q / 'vmlinuz-lite-qemu'),
               '-initrd', str(q / 'lite-initramfs.cpio.gz'), '-append',
               'console=ttyS0 quiet net.ifnames=0 biosdevname=0', '-display', 'none',
               '-serial', 'stdio', '-no-reboot', '-nic', 'user,model=e1000',
               '-drive', f'file={q / "data.img"},format=raw,if=virtio',
               '-fw_cfg', f'name=lite_args,file=/proc/self/fd/{fd}']
        return subprocess.Popen(cmd, stdin=tty, stdout=tty, stderr=tty, env=env,
                                pass_fds=(fd,), start_new_session=True)
    finally:
        os.close(fd)
