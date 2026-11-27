# Sürüm notları

## v0.1.0 — İlk kaynak sürümü

- Windows ve Linux için Türkçe/İngilizce GTK 4 arayüzü: indirme kuyruğu, etkin parça göstergesi ve `amdl` v0.1.4 için 53 açıklamalı ayar.
- Hesap ekranı ve Apple istediğinde altı haneli doğrulama alanı. GUI giriş bilgilerini ana makinenin komut satırına yazmaz. Wrapper oturum token’larını yerel ve şifrelenmemiş diskte tutar.
- Windows x64 ve Linux x86_64 için yerel taşınabilir derleme betikleri; hareketli kapakları işlemek için paketlenen FFmpeg.
- Sistem, Açık ve Koyu temaları olan proje sitesi; iki dilli kullanım kılavuzu ve geliştirici devir notları.

**Bu bir kaynak sürümüdür.** Üçüncü taraf `amdl` motorunun yeniden dağıtım izni doğrulanmadığı için hazır Windows ZIP ve Linux TAR.GZ eklenmedi. [Yerel derleme adımları](README.md#geliştirme--development) depoda bulunur.

**Doğrulama:** Yedi birim testi geçti. Linux taşınabilir arayüzü ve FFmpeg denendi. Windows x64 paketi üretildi ve bağımlılıkları statik olarak denetlendi; gerçek Windows açılışı, canlı Apple hesabı girişi ve indirme doğrulanmadı.

**English:** First source release, with a bilingual GTK frontend, a 2FA prompt, portable build scripts and a dark-mode project site. No prebuilt archives are attached. Linux GUI and FFmpeg were exercised; native Windows launch and live Apple sign-in remain unverified.
