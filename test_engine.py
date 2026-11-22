"""Hesap veya gerçek indirme kullanmayan testler."""
from http.server import BaseHTTPRequestHandler, HTTPServer
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

    def test_invalid_credentials_are_not_spawned(self):
        for email, password in [('a:b', 'pw'), ('demo@example.invalid', 'pw\n')]:
            with self.assertRaises(ValueError):
                engine.login_process(Path('/'), email, password, -1)


if __name__ == '__main__':
    unittest.main()
