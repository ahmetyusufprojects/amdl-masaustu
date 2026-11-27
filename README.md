# amdl Masaüstü / amdl Desktop

**Apple Music bağlantılarından indirme yapmak için Türkçe ve İngilizce bir Windows ve Linux masaüstü uygulaması.** `amdl` indirme motoruna GTK 4 arayüzü ekler. Birden fazla bağlantı sıraya alınabilir; üst çubuk etkin parçanın ilerlemesini gösterir. Bu bir canlı müzik oynatıcısı değildir.

[Proje sitesi](https://ahmetyusufprojects.github.io/amdl-masaustu/) · [Kaynak sürümleri](https://github.com/ahmetyusufprojects/amdl-masaustu/releases) · [English](#english) · [Taşınabilir paket](#taşınabilir-paket) · [Gizlilik](#gizlilik) · [Geliştirici devir notları](AGENTS.md)

## Taşınabilir paket

GitHub Releases kaynak kodunu ve mevcut Windows taşınabilir kurulumları için motor içermeyen arayüz güncellemesini sunar. `amdl` motorunun yeniden dağıtım izni doğrulanmadığı için tam ZIP ve TAR.GZ dosyaları yayımlanmaz. Aşağıdaki yönergeler [yerelde üretilen paketler](#geliştirme--development) içindir.

**Mevcut Windows paketini güncellemek için:** Uygulamayı kapat, güncelleme ZIP’ini çıkar ve içindeki `app` klasörü ile `amdl-masaustu.exe` dosyasını mevcut paketin köküne kopyala; aynı adlı dosyaları değiştir. `motor/` ve `runtime/` olduğu gibi kalır. Tekrar sorun yaşarsan **Hesap → Giriş tanılama kaydını aç**. `motor/giris-tani.log` yalnızca son denemenin aşamalarını ve hata kodunu tutar; ham çıktı veya hesap bilgileri yazılmaz.

| Sistem | Arşivi tamamen çıkardıktan sonra |
| --- | --- |
| Windows 10/11 x64 | `amdl-Masaustu-windows-x64.zip` içindeki **`amdl-masaustu.exe`** dosyasına çift tıkla. |
| Linux x86_64 | `amdl-Masaustu-linux-x64.tar.gz` içindeki **`amdl-masaustu`** dosyasını aç. Arayüz Ubuntu 24.04 tabanında derlenir; uyumlu bir Wayland veya X11 grafik sistemi gerekir. |

Python, GTK 4, `amdl`, QEMU ve FFmpeg klasöre dahildir. Kurulum veya kullanım için terminal komutu gerekmez. Klasörü yazılabilir bir konuma çıkar ve çalıştırılabilir dosyayı diğer dosyalardan ayırma. Windows çalıştırılabilir dosyası imzasızdır. Arşivlerin SHA‑256 özetleri yanlarında verilir.

Parola, token ve önceki indirmeler paketlere aktarılmaz. İlk kullanımda **Hesap** sekmesine git. Ayarlar, oturum diski ve varsayılan çıktı klasörleri çıkarılan klasörün `motor/` dizininde kalır; giriş yaptığın kopyayı paylaşma.

## Linux menü kısayolu (isteğe bağlı)

Taşınabilir paket yerine mevcut Linux motorunu kullanarak uygulama menüsüne kısayol ekleyebilirsin.

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
- Hesap ekranı Apple’a ait değildir; üçüncü taraf wrapper kullanır. Masaüstü uygulaması parolayı süreç argümanına veya yapılandırmaya yazmaz. Giriş ilerlerken QEMU misafirinin seri hattına aktarır ve giriş argümanları misafirin RAM’inde tutulur. Wrapper oturum token’larını ise şifrelenmemiş diske yazar. `wrapper-lite/qemu/data.img` dosyasını ve logları paylaşma. İstasyon veya API token’ı girersen, değer yerel `config.yaml` içine kaydedilir.
- Motorlar Apple’a bağlanır; `amdl` sürüm bildirimi için GitHub’a da bağlanabilir. Yalnızca indirme hakkın olan içerikleri, geçerli koşullara ve yasalara uygun şekilde indir. Bu proje Apple ile ilişkili değildir.

## English

A bilingual GTK 4 Windows and Linux frontend for the [amdl](https://github.com/zhaarey/apple-music-downloader) engine and [wrapper-lite](https://github.com/WorldObservationLog/wrapper/tree/lite). It queues links, tracks active download progress in the header, and exposes the v0.1.4 YAML settings in a categorized interface. It is not a streaming player.

**Portable.** GitHub Releases provides source code and an engine-free update for existing Windows installations. Close the app and copy `app/` and `amdl-masaustu.exe` from the update ZIP into the existing bundle. For full portable archives, build locally using the instructions below; the bundled engine has no verified redistribution license. Extract the archive for your platform to a writable folder. Open `amdl-masaustu.exe` on Windows 10/11 x64 or `amdl-masaustu` on Linux x86_64. Keep the whole folder together. Python, GTK, QEMU and FFmpeg are included. The Windows launcher is unsigned. The Linux build uses Ubuntu 24.04 as its baseline and requires a compatible Wayland or X11 environment. Local data lives under `motor/`.

**Optional Linux menu shortcut.** On Ubuntu/Debian: `sudo apt install python3-gi gir1.2-gtk-4.0 python3-yaml`. From the checkout run `/usr/bin/python3 -Es install.py --runtime /absolute/engine/path`, or `/usr/bin/python3 -Es install.py --fetch` to download SHA‑256-checked Linux x86_64 dependencies (authenticated GitHub CLI required). If the upstream Actions artifact expires, obtain a compatible QEMU bundle upstream and use `--runtime`. Launch **amdl Desktop** from the application menu. FFmpeg is optional unless you enable conversion or motion artwork.

**Use.** Open **Account** to sign in and enter a verification code if requested. Then paste Apple Music URLs, one per line, on **Download**. Choose ALAC, Atmos or AAC, and start the queue. The header reports progress for the current track, not the entire queue. The local service starts when needed. **Settings** has field descriptions and **Guide** has examples. Switch languages using the header button.

**Privacy.** The frontend does not upload telemetry. It uses a third-party account flow, not an official Apple sign-in screen. The GUI sends sign-in input through the VM's serial connection, not the host command line or configuration. The wrapper stores session tokens on its unencrypted guest disk. Keep `config.yaml` and `wrapper-lite/qemu/data.img` private. The local unauthenticated API should not be exposed. The upstream engines contact Apple and amdl can check GitHub for version notices. Only download content you are entitled to download.

## Geliştirme / Development

```bash
/usr/bin/python3 -Es -m unittest discover -v
/usr/bin/python3 -Es desktop.py --smoke-test
```

GTK smoke testi çalışan bir Wayland/X11 oturumu gerektirir. / The GTK smoke test requires a Wayland or X11 session.

Linux x86_64 derleme makinesinde iki taşınabilir paketi üretmek için:

```bash
/usr/bin/python3 -Es packaging/build.py all
```

Derleme için Python 3.12+, PyYAML, `curl`, `zstd`, `bwrap`, `glib-compile-schemas`, `update-mime-database` ve doğrulanmış bir `gh` oturumu gerekir. Linux derlemesinde kullanıcı ad alanlarına izin veren bir sistem gerekir. Motor dosyaları güvenilir kaynaklardan indirilip SHA‑256 ile denetlenir. Uygulama, sıfırdan oluşturulan `dist/` klasörlerine yerel kullanıcı ayarlarını kopyalamaz. Sabitlenmiş upstream GitHub Actions paketi zamanla sona erebilir; bu durumda yeni doğrulanmış bir paket sürümüne geçmek gerekir.
