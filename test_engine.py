"""Hesap veya gerçek indirme kullanmayan testler."""
import gzip
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import tempfile
import threading
import unittest

import engine
from settings import FIELDS, get, put


class Tests(unittest.TestCase):
    def test_links(self):
        self.assertTrue(engine.is_link('https://music.apple.com/tr/album/sample/123?i=124'))
        for url in ('--update', 'http://music.apple.com/tr/song/42', 'https://music.apple.com.evil.example/42',
                    'https://music.apple.com@evil.example/42', 'https://music.apple.com/', 'https://music.apple.com/a b'):
            self.assertFalse(engine.is_link(url))

    def test_progress(self):
        self.assertEqual(engine.PERCENT.search('Decrypting...  5% (1.3/23 MB)').group(1), '5')
        self.assertEqual(engine.SUMMARY.search('Completed: 4/5 | Warnings: 0 | Errors: 1').groups(), ('4', '5', '1'))
        self.assertEqual(engine.ANSI.sub('', '\x1b[2KProcessing'), 'Processing')

    def test_config(self):
        data = {'custom': {'key': 'preserved'}}
        paths = {row[0] for row in FIELDS}
        self.assertEqual(len(paths), len(FIELDS))
        for key, default, *_ in FIELDS:
            put(data, key, default)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.yaml'
            engine.write_yaml(path, data)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            restored = engine.read_yaml(path)
        self.assertEqual(restored, data)
        self.assertIs(get(restored, 'media.alac-fix'), True)

    def test_status(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == '/redirect/status':
                    self.send_response(302)
                    self.send_header('Location', '/status')
                    self.end_headers()
                    return
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"code":0,"data":{"regions":["tr"]}}')

        with HTTPServer(('127.0.0.1', 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f'http://127.0.0.1:{server.server_port}'
                self.assertEqual(engine.status(url), ['tr'])
                self.assertIsNone(engine.status(url + '/redirect'))
            finally:
                server.shutdown()
                thread.join()

    def test_login_payload(self):
        for email, password in [('a:b', 'pw'), ('demo@example.invalid', 'pw\n'), ('a', '\x03'), ('a', 'x' * 5000)]:
            with self.assertRaises(ValueError):
                engine.login_payload(email, password)
        self.assertEqual(engine.login_payload('demo@example.invalid', ' a:b '),
                         b'4\n--login\ndemo@example.invalid: a:b \n--base-dir\n/data\n')

    def test_login_output_split_and_deduplicated(self):
        output = engine.LoginOutput()
        self.assertEqual(output.feed(b'noise AMDL_LOGIN_'), [])
        self.assertEqual(output.feed(b'READY\n2FA co'), ['guest_ready'])
        self.assertEqual(output.feed(b'de: '), ['code_requested'])
        self.assertEqual(output.feed(b'2FA code: account info cached successfully'), ['session_cached'])
        self.assertEqual(output.feed(b'Enter your 2FA code into /data/2fa.txt'), ['unsupported_code_mode'])
        self.assertEqual(output.feed(b'data disk mount failed'), ['guest_disk_mount_failed'])

    def test_login_diagnostics_only_store_known_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            engine.login_log(path, 'started')
            for event, detail in [('secret@example.invalid', None), ('code_sent', '123456')]:
                with self.assertRaises(ValueError):
                    engine.login_log(path, event, detail)
            engine.login_log(path, 'exited', 1)
            log = path / 'giris-tani.log'
            self.assertEqual([line.split(maxsplit=2)[-1] for line in log.read_text().splitlines()], ['started', 'exited 1'])
            engine.login_log(path, 'started')
            self.assertNotIn('exited', log.read_text())

    def test_cpio_newc(self):
        data = gzip.decompress(engine.cpio_overlay({'init': b'demo'}))
        self.assertTrue(data.startswith(b'070701'))
        self.assertEqual(int(data[6 + 6 * 8:6 + 7 * 8], 16), 4)
        self.assertEqual(data[110:115], b'init\0')
        self.assertEqual(data[116:120], b'demo')
        self.assertIn(b'TRAILER!!!\0', data)

    def test_local_qemu_and_bundled_ffmpeg(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            (runtime / 'bin').mkdir()
            self.assertEqual(engine.child_env(runtime)['PATH'].split(os.pathsep)[0], str(runtime / 'bin'))
            cmd = engine.service_command(runtime, 31415)
            self.assertEqual(cmd[1:], ['--host', '127.0.0.1', '--host-port', '31415', '--guest-port', '12340'])
            cmd, _ = engine.qemu_command(runtime, runtime / 'tmp.img')
            self.assertNotIn('hostfwd', ' '.join(cmd))
            self.assertIn('rdinit=/amdl-login-init', ' '.join(cmd))


if __name__ == '__main__':
    unittest.main()
