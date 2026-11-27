# Geliştirici ve ajan devir notları

Bu depo, `amdl` v0.1.4 ve `wrapper-lite` için Türkçe/İngilizce bir GTK 4 istemcisidir. Motorların kaynak deposu değildir. Projenin kullanıcı kılavuzu [README.md](README.md), GitHub Pages sitesi [`docs/`](docs/) altındadır (`main:/docs`).

## Dosya haritası

| Dosya | Sorumluluk |
| --- | --- |
| `desktop.py` | GTK arayüzü, çeviriler, indirme kuyruğu, etkin parça ilerlemesi, Hesap ve 2FA akışı. Arka plan işlerinden GTK güncellemeleri `GLib.idle_add` ile yapılır. |
| `engine.py` | YAML, URL doğrulama, loopback `/status`, alt süreçler, runtime kilidi, QEMU servis/giriş akışı. |
| `settings.py` | Upstream v0.1.4 ile eşleşen 53 ayarın yolları, varsayılanları, açıklamaları ve gizli alan listesi. |
| `portable.py`, `install.py` | Taşınabilir açılış ve isteğe bağlı Linux menü kısayolu. Windows `.exe` açıcı `packaging/windows_launcher.c` içindedir. |
| `packaging/` | Karma değerleri sabitlenmiş bileşenleri sağlayan, temiz runtime ve arşiv üreten derleme betikleri. |
| `test_engine.py` | Motora ve gerçek hesaba ihtiyaç duymayan birim testleri. |

## Davranış ve veri sınırları

- Girişte Apple isterse 6 haneli kod alanı açılır. GUI parolayı host argümanına, ortama ve yapılandırmaya yazmaz; seri erişimden VM’ye iletir. Wrapper token’ları şifrelenmemiş `wrapper-lite/qemu/data.img` dosyasında saklar. Giriş ve hata denemelerinde gerçek kimlik bilgilerini isteme veya loglama. Eski upstream launcher’ın parola taşıma yöntemini GUI’ye geri getirme.
- Runtime `--runtime` ile seçilebilir. Taşınabilir kopyalarda `motor/` kullanılır. Mevcut runtime’dan ayar, oturum diski veya indirme kopyalayarak paket üretme. `config.yaml`, `ui.yaml`, `.lite-qemu-args`, token’lar, disk imajları, girişli klasörler ve indirmeler özel veridir.
- `media-user-token` istasyonlar için kullanılır; wrapper girişinin yerine geçmez. Yerel servis varsayılan olarak `127.0.0.1:12340` üzerinde çalışır ve API kimlik doğrulaması yoktur. Servisi ağda açma. `/status` içindeki boş `regions`, oturum yok demektir.
- Ayar değişikliklerini Türkçe ve İngilizce birlikte güncelle. Üst ilerleme çubuğu bütün kuyruğu değil etkin parçayı temsil eder.

## Test ve sürüm kontrolü

1. `/usr/bin/python3 -Es -m unittest discover -v` ve `git diff --check` çalıştır. Grafik oturumu varsa `/usr/bin/python3 -Es desktop.py --smoke-test` ile GUI’yi doğrula. Hesap testi için boş runtime kullan ve yalnızca doğrulanan kapsamı bildiren sürüm notu yaz.
2. Gerekirse Linux x64 derleme makinesinde `/usr/bin/python3 -Es packaging/build.py all --out /yazılabilir/boş/dizin` çalıştır. Çıkan `.sha256` dosyalarını kontrol et. Upstream Actions artefaktı sona ererse doğrulanmış yeni artefakt ve özet gerekir; kontrolü devre dışı bırakma.
3. Bir paket başarılı biçimde derlense bile platform çalıştırma testi ayrı bir kontroldür. Linux taşınabilir GUI ve FFmpeg denenmiştir. Windows x64 paketi statik olarak denetlenmiştir; yerel Windows açılışı ve canlı Apple/2FA akışı henüz doğrulanmadı. Wine’ın kendi başlatma hatası bir Windows uygulama sonucu değildir.
4. `amdl` v0.1.4 için yeniden dağıtım izni doğrulanmadı. Bu değişmeden motor içeren arşivleri Releases’e ekleme. Windows arayüz güncellemesi yalnızca projenin kendi başlatıcısını ve `app/` kaynaklarını içerebilir. Yanlışlıkla eklenen özel dosya olmadığını `git diff --cached --name-status` ve `git ls-files` ile denetle. `giris-tani.log` yalnızca sabit olay adları ve sayısal süreç/hata kodları içerir; ham wrapper çıktısı ekleme.
5. Siteyi değiştirdiğinde açık/koyu/sistem seçimlerini, yenileme sonrası seçimin korunmasını ve dar ekran düzenini kontrol et. GitHub’ın kendi depo arayüzünün teması kullanıcı ayarlarından yönetilir.
