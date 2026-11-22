# amdl Masaüstü / amdl Desktop

**Apple Music bağlantılarından indirme yapmak için iki dilli bir Linux masaüstü uygulaması.** `amdl` indirme motoruna GTK 4 arayüzü ekler. Birden fazla bağlantı sıraya alınabilir; üst çubuk etkin parçanın ilerlemesini gösterir. Bu bir canlı müzik oynatıcısı değildir.

[English](#english) · [Kurulum](#kurulum) · [Gizlilik](#gizlilik)

## Kurulum

Gerekenler: Linux x86_64, Python 3.11+, GTK 4, PyGObject ve PyYAML. Ubuntu/Debian örneği:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 python3-yaml
```

Klonladıktan sonra aşağıdaki yöntemlerden **birini** kullan:

```bash
# Hazır amdl + wrapper-lite klasörün varsa:
/usr/bin/python3 -Es install.py --runtime /mutlak/yol/motor

# Sıfırdan kurulum: gh kurulu ve GitHub oturumu açık olmalı.
/usr/bin/python3 -Es install.py --fetch
```

Kurulum sistem dizinlerine yazmaz; uygulama menüsüne **amdl Masaüstü** ekler. `--runtime` klasöründe `amdl`, `wrapper-lite/wrapper-lite-qemu` ve `wrapper-lite/qemu/` olmalı. Mevcut `config.yaml` kurulurken değiştirilmez. `--fetch` sabitlenmiş paketleri SHA‑256 ile doğrular. Upstream Actions paketi artık erişilemiyorsa [wrapper-lite derleme/kurulum belgelerine](https://github.com/WorldObservationLog/wrapper/tree/lite) ve [amdl sürümlerine](https://github.com/zhaarey/apple-music-downloader/releases) bak; ardından `--runtime` kullan. Arayüz `amdl` v0.1.4 ve Linux x86_64 QEMU paketi için tasarlanmıştır.

Dönüştürme ve hareketli kapak için ayrıca `sudo apt install ffmpeg`. Temel indirmeler için FFmpeg veya Go gerekmez.

## Kullanım

1. **Hesap** sekmesinde giriş yap. Apple isterse altı haneli kodu gir. Yerel oturum önbelleği daha sonraki indirmelerde kullanılır. Tarayıcıdan aldığın `media-user-token` yalnızca istasyonlar için isteğe bağlıdır; bu girişin yerine geçmez.
2. **İndir** sekmesine her satıra bir `https://music.apple.com/…` bağlantısı ekle. ALAC, Dolby Atmos veya AAC seç. Yerel servis gerektiğinde başlar. Başka bir süreç aynı motoru çalıştırıyorsa önce gerekirse o süreci durdur.
3. Üstteki yüzde etkin parçayı gösterir, tüm kuyruğun yüzdesini değil. Motor yüzde bildirmiyorsa çubuk belirsiz ilerleme gösterir. **İşlem günlüğü** yalnızca pencere oturumu boyunca tutulur. İptal edilen işin kısmi dosyaları kalabilir.
4. **Ayarlar** sekmesinde ağ, ses/video kalitesi, klasör ve isim şablonları, sözler, kapaklar, etiketler ve FFmpeg ayarları var. **Ayarları kaydet** değişiklikleri sonraki işe uygular. **Rehber** bölümünde örnekler ve uyarılar bulunur. Sağ üstten uygulama dilini değiştir.

## Gizlilik

- Arayüz telemetri veya çökme kaydı yüklemez. Depo çalıştırılabilir dosya, kullanıcı yapılandırması, token, QEMU oturum diski veya indirilmiş içerik içermez.
- Yerel wrapper `127.0.0.1:12340` adresine bağlanır. API kimlik doğrulaması yoktur; portu ağda paylaşma, uzak wrapper adresi seçersen yöneticisine güvenmen gerekir. Uygulama kapanınca kendi başlattığı servisi durdurur, haricî servisleri durdurmaz.
- Hesap ekranı Apple’a ait değildir; üçüncü taraf wrapper kullanır. Masaüstü uygulaması giriş parolasını ana makinede süreç argümanına yazmaz; QEMU’ya geçici bir bellek dosyasıyla iletir. Upstream misafir yazılımı giriş argümanlarını ve token’ları şifrelenmemiş oturum diskine yazabilir. `wrapper-lite/qemu/data.img` dosyasını ve logları paylaşma. İstasyon veya API token’ı girersen, değer mevcut yerel `config.yaml` içine kaydedilir.
- Motorlar Apple’a bağlanır; `amdl` sürüm bildirimi için GitHub’a da bağlanabilir. Yalnızca indirme hakkın olan içerikleri, geçerli koşullara ve yasalara uygun şekilde indir. Bu proje Apple ile ilişkili değildir.

## English

A bilingual GTK 4 Linux frontend for the [amdl](https://github.com/zhaarey/apple-music-downloader) engine and [wrapper-lite](https://github.com/WorldObservationLog/wrapper/tree/lite). It queues links, tracks active download progress in the header, and exposes the v0.1.4 YAML settings in a categorized interface. It is not a streaming player.

**Install.** On Ubuntu/Debian: `sudo apt install python3-gi gir1.2-gtk-4.0 python3-yaml`. From the checkout run `/usr/bin/python3 -Es install.py --runtime /absolute/engine/path`, or `/usr/bin/python3 -Es install.py --fetch` to download SHA‑256-checked Linux x86_64 dependencies (authenticated GitHub CLI required). If the upstream Actions artifact expires, obtain a compatible QEMU bundle upstream and use `--runtime`. Launch **amdl Desktop** from the application menu. FFmpeg is optional unless you enable conversion or motion artwork.

**Use.** Open **Account** to sign in and enter a verification code if requested. Then paste Apple Music URLs, one per line, on **Download**. Choose ALAC, Atmos or AAC, and start the queue. The header reports progress for the current track, not the entire queue. The local service starts when needed. **Settings** has field descriptions and **Guide** has examples. Switch languages using the header button.

**Privacy.** The frontend does not upload telemetry. It uses a third-party account flow, not an official Apple sign-in screen. The GUI does not put the password on the host command line, but the unencrypted guest disk may retain credentials and session data. Keep `config.yaml` and `wrapper-lite/qemu/data.img` private. The local unauthenticated API should not be exposed. The upstream engines contact Apple and amdl can check GitHub for version notices. Only download content you are entitled to download.

## Geliştirme / Development

```bash
/usr/bin/python3 -Es -m unittest discover -v
/usr/bin/python3 -Es desktop.py --smoke-test
```

GTK smoke testi çalışan bir Wayland/X11 oturumu gerektirir. / The GTK smoke test requires a Wayland or X11 session.
