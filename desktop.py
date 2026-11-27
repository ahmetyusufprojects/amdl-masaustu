#!/usr/bin/python3
"""GTK 4 indirme merkezi."""
import argparse
import codecs
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import threading
import time

import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gio, GLib, Gtk

import engine
from settings import FIELDS, SECRET, get, put

APP = 'io.github.AmdlMasaustu'
GROUPS = {
    'general': ('Hesap ve bağlantı', 'Account and connection'),
    'media': ('Ses ve video kalitesi', 'Audio and video quality'),
    'paths': ('Klasörler ve dosya adları', 'Folders and filenames'),
    'metadata.lyrics': ('Şarkı sözleri', 'Lyrics'),
    'metadata.artwork': ('Kapak görselleri', 'Artwork'),
    'metadata.tags': ('Meta veri etiketleri', 'Metadata tags'),
    'convert': ('İndirme sonrası dönüştürme', 'Post-download conversion'),
}
CSS = b'''
headerbar { border-bottom: 1px solid alpha(currentColor,.13); }
.hero { padding: 22px; border-radius: 18px; background: alpha(@accent_bg_color,.12); }
.card { padding: 16px; border-radius: 12px; background: alpha(currentColor,.055); }
.muted { opacity: .72; }
'''


def box(vertical=True, space=12):
    return Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL, spacing=space)


def label(text, style=None):
    w = Gtk.Label(label=text, xalign=0, wrap=True, selectable=False)
    if style:
        w.add_css_class(style)
    return w


def margins(w, value=20):
    w.set_margin_top(value)
    w.set_margin_bottom(value)
    w.set_margin_start(value)
    w.set_margin_end(value)
    return w


def scroll(content):
    s = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
    s.set_child(margins(content))
    return s


def button(text, callback, style=None):
    b = Gtk.Button(label=text)
    b.connect('clicked', callback)
    if style:
        b.add_css_class(style)
    return b


class App(Gtk.Application):
    def __init__(self, args):
        super().__init__(application_id=APP, flags=Gio.ApplicationFlags.NON_UNIQUE if args.smoke_test else Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.runtime = args.runtime.resolve()
        self.config_file = self.runtime / 'config.yaml'
        self.smoke = args.smoke_test
        self.prefs = (self.runtime / 'ui.yaml' if getattr(args, 'portable', False) else
                      Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'amdl-masaustu' / 'ui.yaml')
        try:
            self.lang = 1 if engine.read_yaml(self.prefs).get('language') == 'en' else 0
        except (OSError, ValueError, engine.yaml.YAMLError):
            self.lang = 0
        self.proc = self.service = self.login = None
        self.service_lock = None
        self.busy = self.account_busy = self.cancelled = self.closing = False
        self.signing_in = self.login_cancelled = False
        self.draft = {}
        self.config_error = False
        self.draft_dirty = False

    def tr(self, tr, en):
        return (tr, en)[self.lang]

    def do_activate(self):
        if getattr(self, 'window', None):
            self.window.present()
            return
        try:
            self.draft = engine.read_yaml(self.config_file)
        except (OSError, ValueError, engine.yaml.YAMLError):
            self.config_error = True
        self.window = Gtk.ApplicationWindow(application=self, title='amdl Masaüstü', default_width=1040, default_height=760)
        self.window.connect('close-request', self.close)
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(self.window.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        action = Gio.SimpleAction.new('quit', None)
        action.connect('activate', lambda *_: self.window.close())
        self.add_action(action)
        self.set_accels_for_action('app.quit', ['<Primary>q'])
        self.build()
        if self.smoke:
            assert len(self.widgets) == len(FIELDS)
            for name in ('download', 'settings', 'account', 'help'):
                self.stack.set_visible_child_name(name)
            self.lang = 1 - self.lang
            self.build()
            assert len(self.widgets) == len(FIELDS)
            self.widgets['media.alac-max'].set_value(48000)
            assert get(self.draft, 'media.alac-max') == 48000
            self.start_btn.emit('clicked')
            assert 'music.apple.com' in self.download_note.get_text()
            self.busy = True
            self.output('Decrypting...   5%')
            assert self.progress.get_text() == '5%'
            self.output('Error detected, press Enter to try again...')
            assert self.retry_btn.get_visible()
            self.finish_download((1, 1, 0), None)
            assert self.progress.get_fraction() == 1
            if os.environ.get('AMDL_SMOKE_SERVICE') == '1':
                self.check_connection(start=True)
                GLib.timeout_add_seconds(10, self.finish_smoke)
            else:
                GLib.idle_add(self.quit)
        else:
            self.window.present()

    def finish_smoke(self):
        if engine.status(engine.LOCAL) is None:
            self.smoke_failed = True
        self.close()
        self.quit()
        return False

    def build(self, page='download'):
        if not hasattr(self, 'progress'):
            bar = Gtk.HeaderBar()
            titles = box(space=1)
            titles.append(label('amdl Masaüstü', 'heading'))
            self.progress = Gtk.ProgressBar(show_text=True, width_request=235)
            titles.append(self.progress)
            bar.set_title_widget(titles)
            self.language_btn = button('', self.toggle_lang)
            bar.pack_end(self.language_btn)
            self.window.set_titlebar(bar)
        self.progress.set_text(self.tr('Etkin indirme yok', 'No active download'))
        self.progress.set_fraction(0)
        self.language_btn.set_label(self.tr('English', 'Türkçe'))
        root = box(space=0)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        switcher = Gtk.StackSwitcher(stack=self.stack, halign=Gtk.Align.CENTER)
        root.append(margins(switcher, 8))
        root.append(self.stack)
        for key, name, content in [
            ('download', self.tr('İndir', 'Download'), self.download_page()),
            ('settings', self.tr('Ayarlar', 'Settings'), self.settings_page()),
            ('account', self.tr('Hesap', 'Account'), self.account_page()),
            ('help', self.tr('Rehber', 'Guide'), self.help_page()),
        ]:
            self.stack.add_titled(scroll(content), key, name)
        self.stack.set_visible_child_name(page)
        self.window.set_child(root)
        self.update_controls()

    def toggle_lang(self, *_):
        if self.busy or self.account_busy:
            return
        urls = self.urls.get_buffer()
        old_links = urls.get_text(urls.get_start_iter(), urls.get_end_iter(), False)
        profile, all_albums, m3u8 = self.mode.get_selected(), self.all_albums.get_active(), self.m3u8.get_active()
        page = self.stack.get_visible_child_name()
        self.lang = 1 - self.lang
        try:
            self.prefs.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            engine.write_yaml(self.prefs, {'language': 'en' if self.lang else 'tr'})
        except OSError:
            pass
        self.build(page)
        self.urls.get_buffer().set_text(old_links)
        self.mode.set_selected(profile)
        self.all_albums.set_active(all_albums)
        self.m3u8.set_active(m3u8)

    def download_page(self):
        page = box()
        hero = box(space=5)
        hero.add_css_class('hero')
        hero.append(label(self.tr('İndirme merkezi', 'Download center'), 'title-1'))
        hero.append(label(self.tr('Apple Music bağlantılarını ekle, ses biçimini seç ve ilerlemeyi üst çubuktan izle.', 'Add Apple Music links, choose a sound profile and follow progress in the top bar.')))
        page.append(hero)
        page.append(label(self.tr('Apple Music bağlantıları · her satıra bir tane', 'Apple Music links · one per line'), 'heading'))
        self.urls = Gtk.TextView(wrap_mode=Gtk.WrapMode.CHAR, monospace=True, top_margin=8, left_margin=8)
        self.urls.set_size_request(-1, 95)
        page.append(Gtk.Frame(child=self.urls))
        controls = box(False)
        self.mode = Gtk.DropDown.new_from_strings([self.tr('ALAC · Kayıpsız', 'ALAC · Lossless'), 'Dolby Atmos', 'AAC'])
        controls.append(self.mode)
        self.all_albums = Gtk.CheckButton(label=self.tr('Sanatçının tüm albümleri', 'All artist albums'))
        self.m3u8 = Gtk.CheckButton(label=self.tr('M3U8 kaydet', 'Save M3U8'))
        controls.append(self.all_albums)
        controls.append(self.m3u8)
        page.append(controls)
        actions = box(False)
        self.start_btn = button(self.tr('İndirmeyi başlat', 'Start download'), self.start_download, 'suggested-action')
        self.stop_btn = button(self.tr('İptal et', 'Cancel'), self.stop_download)
        self.retry_btn = button(self.tr('Yeniden dene', 'Retry'), self.retry_download)
        self.retry_btn.set_visible(False)
        for w in (self.start_btn, self.stop_btn, self.retry_btn, button(self.tr('Çıktı klasörünü aç', 'Open output folder'), self.open_output)):
            actions.append(w)
        page.append(actions)
        self.download_note = label(self.tr('Yalnızca indirme hakkın olan içerikleri indir.', 'Only download content you are entitled to download.'), 'muted')
        page.append(self.download_note)
        self.log = Gtk.TextView(editable=False, cursor_visible=False, monospace=True, wrap_mode=Gtk.WrapMode.CHAR)
        log_scroll = Gtk.ScrolledWindow(min_content_height=130, vexpand=True, child=self.log)
        page.append(Gtk.Expander(label=self.tr('İşlem günlüğü · yalnızca bu oturum', 'Activity log · this session only'), child=log_scroll))
        return page

    def settings_page(self):
        page = box()
        page.append(label(self.tr('İndirme ayarları', 'Download settings'), 'title-1'))
        page.append(label(self.tr('Her alanın ne yaptığını ve hangi koşullarda çalıştığını aşağıda görebilirsin. Kaydedilen değişiklikler bir sonraki indirmeye uygulanır.', 'Each field explains what it does and when it applies. Saved changes take effect on the next download.'), 'muted'))
        toolbar = box(False)
        self.save_btn = button(self.tr('Ayarları kaydet', 'Save settings'), self.save_settings, 'suggested-action')
        toolbar.append(self.save_btn)
        self.settings_note = label(self.tr('Kaydetmeden çıkarsan değişiklikler uygulanmaz.', 'Unsaved changes are not applied.'))
        toolbar.append(self.settings_note)
        page.append(toolbar)
        ffmpeg = get(self.draft, 'convert.ffmpeg-path', 'ffmpeg')
        if not isinstance(ffmpeg, str) or not shutil.which(ffmpeg, path=engine.child_env(self.runtime).get('PATH')):
            page.append(label(self.tr('FFmpeg bulunamadı. Dönüştürme ve hareketli kapak seçenekleri FFmpeg kurulana kadar çalışmaz.', 'FFmpeg not found. Conversion and motion artwork require FFmpeg.'), 'muted'))
        self.widgets = {}
        if self.config_error:
            self.settings_note.set_text(self.tr('config.yaml okunamadı. Dosya üzerine yazılmayacak.', 'Could not read config.yaml. The file will not be overwritten.'))
        elif self.draft_dirty:
            self.settings_note.set_text(self.tr('Kaydedilmemiş değişiklikler var.', 'There are unsaved changes.'))
        for key, titles in GROUPS.items():
            card = box(space=15)
            card.add_css_class('card')
            for path, default, choices, tr, en, tr_help, en_help in FIELDS:
                if path.rsplit('.', 1)[0] != key and not (key == 'media' and path.startswith('media.mv.')):
                    continue
                row = box(False, 15)
                description = box(space=4)
                description.set_hexpand(True)
                description.append(label(self.tr(tr, en), 'heading'))
                description.append(label(self.tr(tr_help, en_help), 'muted'))
                row.append(description)
                value = get(self.draft, path, default)
                if type(default) is bool:
                    retained = bool(value)
                    widget = Gtk.Switch(active=retained, valign=Gtk.Align.CENTER)
                    widget.connect('notify::active', lambda w, _, p=path: self.setting_changed(p, w.get_active()))
                elif choices:
                    values = choices if value in choices else (*choices, value)
                    widget = Gtk.DropDown.new_from_strings([str(v) if v != '' else self.tr('Kapalı', 'Off') for v in values])
                    widget.set_selected(values.index(value))
                    widget.connect('notify::selected', lambda w, _, p=path, vs=values: self.setting_changed(p, vs[w.get_selected()]))
                elif type(default) is int:
                    widget = Gtk.SpinButton.new_with_range(1, 2_147_483_647, 1)
                    widget.set_value(value if type(value) is int else default)
                    widget.connect('value-changed', lambda w, p=path: self.setting_changed(p, w.get_value_as_int()))
                else:
                    widget = Gtk.Entry(text=str(value), width_chars=18, visibility=path not in SECRET)
                    widget.connect('changed', lambda w, p=path: self.setting_changed(p, w.get_text()))
                widget.set_valign(Gtk.Align.CENTER)
                row.append(widget)
                self.widgets[path] = widget
                card.append(row)
            group = Gtk.Expander(label=titles[self.lang], child=card)
            group.set_expanded(key == 'general')
            page.append(group)
        return page

    def setting_changed(self, path, value):
        put(self.draft, path, value)
        self.draft_dirty = True
        self.settings_note.set_text(self.tr('Kaydedilmemiş değişiklikler var.', 'There are unsaved changes.'))

    def save_settings(self, *_):
        if self.config_error:
            return
        try:
            engine.write_yaml(self.config_file, self.draft)
            self.draft_dirty = False
            self.settings_note.set_text(self.tr('Ayarlar kaydedildi.', 'Settings saved.'))
        except (OSError, engine.yaml.YAMLError):
            self.settings_note.set_text(self.tr('Yapılandırma kaydedilemedi.', 'Could not save configuration.'))

    def account_page(self):
        page = box()
        page.append(label(self.tr('Hesap ve bağlantı', 'Account and connection'), 'title-1'))
        page.append(label(self.tr('Bir kez giriş yap. Yerel wrapper sonraki indirmelerde oturumu yeniden kullanır.', 'Sign in once. The local wrapper reuses the session for later downloads.')))
        card = box()
        card.add_css_class('card')
        card.append(label(self.tr('Apple hesabı e-postası', 'Apple Account email')))
        self.email = Gtk.Entry(input_purpose=Gtk.InputPurpose.EMAIL)
        card.append(self.email)
        card.append(label(self.tr('Apple hesabı parolası', 'Apple Account password')))
        self.password = Gtk.PasswordEntry(show_peek_icon=True)
        self.password.connect('activate', self.sign_in)
        card.append(self.password)
        self.sign_btn = button(self.tr('Giriş yap', 'Sign in'), self.sign_in, 'suggested-action')
        self.cancel_login_btn = button(self.tr('Girişi iptal et', 'Cancel sign-in'), self.cancel_login)
        login_actions = box(False)
        login_actions.append(self.sign_btn)
        login_actions.append(self.cancel_login_btn)
        card.append(login_actions)
        self.code_row = box()
        self.code_row.append(label(self.tr('Tek kullanımlık doğrulama kodu', 'One-time verification code')))
        self.code = Gtk.Entry(max_length=6, input_purpose=Gtk.InputPurpose.DIGITS, visibility=False)
        self.code.connect('activate', self.submit_code)
        self.code_row.append(self.code)
        self.code_row.append(button(self.tr('Kodu gönder', 'Submit code'), self.submit_code))
        self.code_row.set_visible(False)
        card.append(self.code_row)
        page.append(card)
        actions = box(False)
        self.check_btn = button(self.tr('Bağlantıyı denetle', 'Check connection'), lambda *_: self.check_connection())
        self.service_btn = button(self.tr('Yerel servisi başlat', 'Start local service'), lambda *_: self.check_connection(start=True))
        self.stop_service_btn = button(self.tr('Servisi durdur', 'Stop service'), self.stop_service)
        for w in (self.check_btn, self.service_btn, self.stop_service_btn):
            actions.append(w)
        page.append(actions)
        self.account_note = label('')
        page.append(self.account_note)
        page.append(label(self.tr('Bu ekran Apple’a ait değildir; hesabı üçüncü taraf wrapper doğrular. Arayüz parolayı komut satırına veya yapılandırmaya yazmaz. Wrapper oturum token’larını şifrelenmeden yerel diskte saklar; motor klasörünü paylaşma.', 'This is not an Apple sign-in screen; a third-party wrapper verifies the account. The UI does not write the password to the command line or configuration. The wrapper stores session tokens unencrypted. Do not share the engine folder.'), 'muted'))
        return page

    def help_page(self):
        page = box()
        page.append(label(self.tr('Kullanım rehberi', 'Field guide'), 'title-1'))
        sections = [
            ('İlk indirme', 'First download', 'Hesap ekranında Apple hesabına giriş yap. İndir ekranına Apple Music şarkı, albüm, liste veya klip bağlantısı yapıştır. Her satır ayrı bir girdidir. Yerel servis gerektiğinde otomatik açılır.', 'Sign in on Account. Paste Apple Music song, album, playlist or video links in Download, one per line. The local service starts on demand.'),
            ('Üst çubuğu oku', 'Read the top bar', 'Yüzde motorun bildirdiği etkin parçaya aittir; tüm listenin yüzdesi değildir. Motor yüzde bildirmediğinde çubuk hareketli bir çalışma göstergesidir. İptal edilen işin kısmi dosyaları kalabilir.', 'The percentage is for the current track, not the full list. When the engine has no percentage, the bar shows indeterminate progress. Canceled jobs may leave partial files.'),
            ('Ses kalitesini seç', 'Choose audio quality', 'ALAC kayıpsız, AAC daha küçük, Dolby Atmos ise uyumlu içerik ve oynatıcı gerektiren uzamsal bir biçimdir. Ayarlardaki üst sınırlar Apple’ın sunmadığı bir kaliteyi oluşturmaz.', 'ALAC is lossless, AAC is smaller, and Dolby Atmos is spatial audio that requires compatible content and playback. Caps cannot create quality unavailable from Apple.'),
            ('Klasörleri kişiselleştir', 'Personalize output folders', 'Örneğin albüm klasörü için {ArtistName} - {AlbumName}, parça adı için {SongNumer}. {SongName} kullanabilirsin. Göreli klasörler motorun bulunduğu dizinden çözülür.', 'Try {ArtistName} - {AlbumName} for albums and {SongNumer}. {SongName} for tracks. Relative paths are resolved from the engine directory.'),
            ('Yerel oturum ve gizlilik', 'Local session and privacy', 'Arayüz telemetri göndermez. Token’lar, indirme ayarları ve oturum diski GitHub’a gönderilmez. Yerel wrapper ağda paylaşılmamalıdır. İstasyon token’ı isteğe bağlıdır ve hesap girişinin yerini tutmaz.', 'The interface sends no telemetry. Tokens, download settings and session disks are not uploaded to GitHub. Do not expose the local wrapper on the network. The optional station token does not replace sign-in.'),
            ('FFmpeg ve dönüşüm', 'FFmpeg and conversion', 'FFmpeg temel indirme için gerekli değildir; dönüştürme veya hareketli kapak için kurulur. Orijinali koru seçeneğini açmadıysan başarılı bir dönüşüm kaynak dosyayı silebilir.', 'FFmpeg is optional for basic downloads but required for conversion or motion artwork. Successful conversion may remove the source unless Keep original is on.'),
        ]
        for tr, en, info_tr, info_en in sections:
            card = box(space=6)
            card.add_css_class('card')
            card.append(label(self.tr(tr, en), 'heading'))
            card.append(label(self.tr(info_tr, info_en)))
            page.append(card)
        return page

    def update_controls(self):
        free = not (self.busy or self.account_busy)
        self.start_btn.set_sensitive(free and not self.config_error)
        self.stop_btn.set_sensitive(self.busy)
        self.language_btn.set_sensitive(free)
        self.sign_btn.set_sensitive(free)
        self.cancel_login_btn.set_visible(self.signing_in)
        self.service_btn.set_sensitive(free and not self.config_error)
        self.check_btn.set_sensitive(free)
        self.stop_service_btn.set_sensitive(free and self.service is not None)
        self.save_btn.set_sensitive(free and not self.config_error)

    def saved(self):
        return engine.read_yaml(self.config_file)

    def ensure_service(self, endpoint, start=True):
        regions = engine.status(endpoint)
        if regions is not None or not start or endpoint.rstrip('/') != engine.LOCAL:
            return regions
        lock = engine.lock_runtime(self.runtime)
        try:
            p = engine.start_service(self.runtime, engine.LOCAL.rsplit(':', 1)[1], lock)
        except OSError:
            lock.close()
            raise
        self.service, self.service_lock = p, lock
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            if self.closing or self.cancelled or p.poll() is not None:
                break
            regions = engine.status(endpoint)
            if regions is not None:
                return regions
            time.sleep(.25)
        self.release_service()
        return None

    def release_service(self):
        p, lock = self.service, self.service_lock
        self.service = self.service_lock = None
        engine.cancel(p, tree=True)
        if p:
            try:
                p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                p.kill()
        if lock:
            lock.close()

    def stop_service(self, *_):
        self.release_service()
        self.account_note.set_text(self.tr('Uygulamanın başlattığı servis durduruldu.', 'The app-managed service was stopped.'))
        self.update_controls()

    def check_connection(self, start=False):
        self.cancelled = False
        self.account_busy = True
        self.update_controls()
        self.account_note.set_text(self.tr('Yerel hizmet bekleniyor…', 'Waiting for local service…'))
        def worker():
            try:
                endpoint = str(get(self.saved(), 'general.lite-server', engine.LOCAL))
                regions = self.ensure_service(endpoint, start)
                if regions:
                    msg = self.tr('Servis hazır. Mağazalar: ', 'Service ready. Storefronts: ') + ', '.join(str(r) for r in regions)
                elif regions == []:
                    msg = self.tr('Servis açık; henüz oturum yok.', 'Service is running; no account session yet.')
                else:
                    msg = self.tr('Servise ulaşılamadı.', 'Could not reach the service.')
            except (OSError, ValueError, engine.yaml.YAMLError):
                msg = self.tr('Servis başlatılamadı. Motor klasörünü ve başka bir oturumun açık olup olmadığını denetle.', 'Could not start service. Check the engine directory and whether another session is active.')
            GLib.idle_add(self.finish_account, msg)
        threading.Thread(target=worker, daemon=True).start()

    def sign_in(self, *_):
        if self.busy or self.account_busy:
            return
        email, password = self.email.get_text().strip(), self.password.get_text()
        try:
            payload = engine.login_payload(email, password)
        except ValueError:
            self.account_note.set_text(self.tr('Geçerli bir e-posta ve parola gir.', 'Enter a valid email and password.'))
            return
        self.password.set_text('')
        self.account_busy = self.signing_in = True
        self.login_cancelled = False
        self.update_controls()
        self.account_note.set_text(self.tr('Apple hesabı doğrulanıyor…', 'Verifying Apple Account…'))
        def worker():
            try:
                self.release_service()
                if self.closing:
                    return
                with engine.lock_runtime(self.runtime), engine.login_process(self.runtime) as proc:
                    self.login = proc
                    if self.closing or self.login_cancelled:
                        engine.cancel(proc)
                    cached = sent = False
                    text = b''
                    while not self.closing and not self.login_cancelled:
                        chunk = proc.stdout.read1(4096)
                        if not chunk:
                            break
                        text += chunk
                        if not sent and engine.LOGIN_READY in text:
                            proc.stdin.write(payload)
                            proc.stdin.flush()
                            sent = True
                        cached |= b'account info cached successfully' in text
                        if b'Enter your 2FA code into' in text:
                            engine.cancel(proc)
                            break
                        if b'2FA code:' in text:
                            text = text.rsplit(b'2FA code:', 1)[-1]
                            GLib.idle_add(self.show_code)
                        text = text[-256:]
                    rc = proc.wait(timeout=5)
                if cached and rc == 0:
                    msg = self.tr('Giriş başarılı. Şimdi indirmeyi başlatabilir veya bağlantıyı denetleyebilirsin.', 'Sign-in succeeded. Start a download or check the connection.')
                else:
                    msg = self.tr('Giriş doğrulanamadı. Hesap bilgilerini ve doğrulama kodunu kontrol et.', 'Sign-in could not be verified. Check your account details and verification code.')
            except (OSError, ValueError, subprocess.TimeoutExpired):
                msg = self.tr('Giriş başlatılamadı. Başka bir wrapper işlemini kapatıp yeniden dene.', 'Could not start sign-in. Stop any other wrapper process and retry.')
            finally:
                self.login = None
            GLib.idle_add(self.finish_account, msg)
        threading.Thread(target=worker, daemon=True).start()

    def cancel_login(self, *_):
        self.login_cancelled = True
        engine.cancel(self.login)
        self.code_row.set_visible(False)
        self.account_note.set_text(self.tr('Giriş iptal ediliyor…', 'Canceling sign-in…'))

    def show_code(self):
        if self.login_cancelled or not self.signing_in:
            return
        self.code_row.set_visible(True)
        self.code.grab_focus()
        self.account_note.set_text(self.tr('Apple doğrulama kodu bekleniyor.', 'Waiting for the Apple verification code.'))

    def submit_code(self, *_):
        code = self.code.get_text()
        proc = self.login
        if proc is None or not re.fullmatch(r'[0-9]{6}', code):
            return
        try:
            proc.stdin.write((code + '\n').encode())
            proc.stdin.flush()
        except (OSError, ValueError):
            return
        self.code.set_text('')
        self.code_row.set_visible(False)
        self.account_note.set_text(self.tr('Kod gönderildi…', 'Code submitted…'))

    def finish_account(self, msg):
        if self.signing_in and self.login_cancelled:
            msg = self.tr('Giriş iptal edildi.', 'Sign-in canceled.')
        self.account_busy = self.signing_in = False
        self.code_row.set_visible(False)
        self.code.set_text('')
        self.account_note.set_text(msg)
        self.update_controls()

    def open_output(self, *_):
        key = ('alac', 'atmos', 'aac')[self.mode.get_selected()]
        try:
            folder = self.runtime / str(get(self.saved(), 'paths.' + key, {'alac': 'AM-Lossless', 'atmos': 'AM-Atmos', 'aac': 'AM-AAC'}[key]))
            folder = folder if folder.is_dir() else self.runtime
            if engine.WINDOWS:
                os.startfile(folder)
            else:
                Gio.AppInfo.launch_default_for_uri(folder.as_uri())
        except (OSError, ValueError, GLib.Error, engine.yaml.YAMLError):
            self.download_note.set_text(self.tr('Çıktı klasörü açılamadı.', 'Could not open the output folder.'))

    def start_download(self, *_):
        if self.busy or self.account_busy:
            return
        buf = self.urls.get_buffer()
        links = [s.strip() for s in buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).splitlines() if s.strip()]
        if not links or not all(engine.is_link(link) for link in links):
            self.download_note.set_text(self.tr('Her satıra geçerli bir https://music.apple.com bağlantısı yaz.', 'Enter one valid https://music.apple.com link per line.'))
            return
        try:
            config = self.saved()
        except (OSError, ValueError, engine.yaml.YAMLError):
            self.download_note.set_text(self.tr('Yapılandırma okunamadı.', 'Could not read configuration.'))
            return
        endpoint = str(get(config, 'general.lite-server', engine.LOCAL))
        args = [str(engine.binary(self.runtime, 'amdl')), '--config', str(self.config_file), '--lite-server', endpoint]
        mode = self.mode.get_selected()
        if mode:
            args.append(('--atmos', '--aac')[mode - 1])
        if self.all_albums.get_active():
            args.append('--all-album')
        if self.m3u8.get_active():
            args.append('--save-m3u8-playlist')
        self.busy = True
        self.cancelled = False
        self.log.get_buffer().set_text('')
        self.download_note.set_text(self.tr('İndirme sırasında bu pencereyi açık tut.', 'Keep this window open during the download.'))
        self.progress.set_text(self.tr('İndirme hazırlanıyor…', 'Preparing download…'))
        self.progress.pulse()
        self.update_controls()
        GLib.timeout_add(180, self.pulse_progress)
        threading.Thread(target=self.download_worker, args=(args + ['--', *links], endpoint, config), daemon=True).start()

    def pulse_progress(self):
        if self.busy and not self.progress.get_text().endswith('%'):
            self.progress.pulse()
        return self.busy

    def download_worker(self, args, endpoint, config):
        summary = None
        failure = None
        secrets = [str(get(config, field, '')) for field in SECRET]
        try:
            regions = self.ensure_service(endpoint)
            if not regions:
                failure = self.tr('Hesap sekmesinde servis bağlantısını ve Apple oturumunu denetle.', 'Check the service connection and Apple session on the Account tab.')
            elif not self.cancelled and not self.closing:
                with subprocess.Popen(args, cwd=self.runtime, env=engine.child_env(self.runtime), stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **engine.process_options()) as proc:
                    self.proc = proc
                    if self.cancelled or self.closing:
                        engine.cancel(proc, tree=True)
                    decoder = codecs.getincrementaldecoder('utf-8')('replace')
                    pending = ''
                    while True:
                        chunk = proc.stdout.read1(4096)
                        if not chunk:
                            break
                        lines = re.split(r'[\r\n]', pending + decoder.decode(chunk))
                        pending = lines.pop()
                        for line in lines:
                            line = engine.ANSI.sub('', line).strip()
                            if not line:
                                continue
                            clean = line
                            for secret in secrets:
                                if secret:
                                    clean = clean.replace(secret, '••••')
                            GLib.idle_add(self.output, clean)
                            if match := engine.SUMMARY.search(line):
                                summary = tuple(map(int, match.groups()))
                    if summary is None or proc.wait() != 0 or summary[2]:
                        failure = self.tr('İndirme tamamlanmadı. İşlem günlüğünü kontrol et.', 'Download did not finish. Check the activity log.')
        except (OSError, ValueError):
            failure = self.tr('Motor çalıştırılamadı. Kurulum klasörünü ve servisi denetle.', 'Could not run the engine. Check the installation directory and the service.')
        self.proc = None
        GLib.idle_add(self.finish_download, summary, failure)

    def output(self, line):
        if not self.busy:
            return
        if 'press Enter to try again' in line:
            self.retry_btn.set_visible(True)
            self.progress.set_text(self.tr('Yeniden deneme bekleniyor', 'Waiting for retry'))
        elif 'Track ' in line:
            self.progress.set_text(self.tr('Parça işleniyor…', 'Processing track…'))
        elif match := engine.PERCENT.search(line):
            progress = min(100, int(match.group(1)))
            self.progress.set_fraction(progress / 100)
            self.progress.set_text(f'{progress}%')
            return
        buf = self.log.get_buffer()
        buf.insert(buf.get_end_iter(), line + '\n')
        if buf.get_line_count() > 500:
            _, end = buf.get_iter_at_line(100)
            buf.delete(buf.get_start_iter(), end)
        self.log.scroll_to_iter(buf.get_end_iter(), 0, False, 0, 0)

    def retry_download(self, *_):
        try:
            if self.proc and self.proc.stdin:
                self.proc.stdin.write(b'\n')
                self.proc.stdin.flush()
        except OSError:
            pass
        self.retry_btn.set_visible(False)

    def stop_download(self, *_):
        self.cancelled = True
        engine.cancel(self.proc, tree=True)
        self.progress.set_text(self.tr('İptal ediliyor…', 'Canceling…'))

    def finish_download(self, summary, failure):
        self.busy = False
        self.retry_btn.set_visible(False)
        if self.cancelled:
            title = self.tr('İptal edildi', 'Canceled')
            note = self.tr('Kısmi dosyalar kalmış olabilir.', 'Partial files may remain.')
        elif failure:
            title, note = self.tr('Tamamlanmadı', 'Not completed'), failure
        else:
            title = self.tr('Tamamlandı', 'Complete')
            note = self.tr(f'{summary[0]}/{summary[1]} parça tamamlandı.', f'{summary[0]}/{summary[1]} tracks completed.')
        self.progress.set_fraction(0 if self.cancelled or failure else 1)
        self.progress.set_text(title)
        self.download_note.set_text(note)
        self.update_controls()

    def close(self, *_):
        self.closing = self.cancelled = True
        engine.cancel(self.proc, tree=True)
        engine.cancel(self.login)
        self.release_service()
        return False


def main(default_runtime=None):
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    default = default_runtime or Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'amdl-masaustu' / 'motor'
    parser.add_argument('--runtime', type=Path, default=default)
    parser.add_argument('--smoke-test', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.portable = default_runtime is not None
    app = App(args)
    signal.signal(signal.SIGTERM, lambda *_: GLib.idle_add(app.window.close) if hasattr(app, 'window') else None)
    result = app.run([])
    return 1 if getattr(app, 'smoke_failed', False) else result


if __name__ == '__main__':
    raise SystemExit(main())
