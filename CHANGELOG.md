# Sürüm notları

## v0.1.2 — Windows giriş bağlantısı

- Windows’ta QEMU giriş bağlantısı yerel adlandırılmış boruya taşındı. Linux aynı seri bağlantıyı kullanmaya devam ediyor.
- Başlatıcı ve arayüz, eksik `app/`, Python, GTK veya QEMU bileşenlerini dosya adıyla bildirir.
- **Windows güncellemesi:** Uygulamayı kapat. ZIP’i çıkar, içindeki `app/` ve `amdl-masaustu.exe` dosyasını mevcut taşınabilir kurulumun köküne kopyala. `motor/` ve `runtime/` klasörlerini değiştirme. ZIP tek başına çalışmaz; üçüncü taraf motoru ve çalışma ortamını içermez.

**Doğrulama:** Wine 11.22 altında `.exe`, GTK, boşluklu kurulum yolu, wrapper başlatma ve kapatma, eksik dosya uyarıları ve QEMU seri komut testi geçti. Gerçek Windows ve canlı Apple girişi/2FA doğrulanmadı.

## v0.1.1 — Giriş tanılama

- Wrapper hazır sinyali vermezse veya giriş ilerlemezse arayüz artık süresiz beklemez. Wrapper doğrulama kodu için desteklenmeyen dosya moduna geçerse ayrı bir mesaj gösterilir.
- **Hesap → Giriş tanılama kaydını aç** son giriş denemesinin aşamalarını gösterir. Dosyada parola, e-posta, token, doğrulama kodu veya ham wrapper çıktısı bulunmaz.
- Windows güncelleme ZIP’i, mevcut taşınabilir uygulamanın arayüzünü günceller; motor ve GTK/Python runtime içermez. Tam taşınabilir paketler, `amdl` motorunun yeniden dağıtım izni doğrulanmadığından yalnızca yerelde üretilir.

**Doğrulama:** Birim testleri ve Linux üzerinde gerçek QEMU misafirine kimlik bilgisi içermeyen seri komut gönderme testi geçti. Windows’ta gerçek Apple girişi doğrulanmadı.

## v0.1.0 — İlk kaynak sürümü

- Windows ve Linux için Türkçe/İngilizce GTK 4 arayüzü: indirme kuyruğu, etkin parça göstergesi ve `amdl` v0.1.4 için 53 açıklamalı ayar.
- Hesap ekranı ve Apple istediğinde altı haneli doğrulama alanı. GUI giriş bilgilerini ana makinenin komut satırına yazmaz. Wrapper oturum token’larını yerel ve şifrelenmemiş diskte tutar.
- Windows x64 ve Linux x86_64 için yerel taşınabilir derleme betikleri; hareketli kapakları işlemek için paketlenen FFmpeg.
- Sistem, Açık ve Koyu temaları olan proje sitesi; iki dilli kullanım kılavuzu ve geliştirici devir notları.

**Bu bir kaynak sürümüdür.** Üçüncü taraf `amdl` motorunun yeniden dağıtım izni doğrulanmadığı için hazır Windows ZIP ve Linux TAR.GZ eklenmedi. [Yerel derleme adımları](README.md#geliştirme--development) depoda bulunur.

**Doğrulama:** Yedi birim testi geçti. Linux taşınabilir arayüzü ve FFmpeg denendi. Windows x64 paketi üretildi ve bağımlılıkları statik olarak denetlendi; gerçek Windows açılışı, canlı Apple hesabı girişi ve indirme doğrulanmadı.

**English:** First source release, with a bilingual GTK frontend, a 2FA prompt, portable build scripts and a dark-mode project site. No prebuilt archives are attached. Linux GUI and FFmpeg were exercised; native Windows launch and live Apple sign-in remain unverified.
