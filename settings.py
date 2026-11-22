"""amdl v0.1.4 için iki dilli ayar kataloğu."""

# Yol, varsayılan değer, seçenekler, adlar ve kullanım açıklamaları.
FIELDS = [
('general.lite-server','http://127.0.0.1:12340',(), 'Wrapper adresi','Wrapper URL','Varsayılan adres yalnızca bu bilgisayara açıktır. Uzak adres kullanırsan sunucunun sahibi isteklerini görebilir.','The default address is local. A remote server operator can see your requests.'),
('general.media-user-token','',(), 'Medya kullanıcı token’ı','Media user token','İstasyonlar için isteğe bağlıdır. Wrapper hesabına giriş yerine geçmez.','Optional for stations; does not replace wrapper sign-in.'),
('general.language','',(), 'İçerik dili','Content language','Örnek: tr-TR veya en-US. Boş bırakırsan mağazanın varsayılanı kullanılır.','Example: tr-TR or en-US. Blank uses the storefront default.'),
('general.max-memory-limit',256,(), 'Bellek tamponu (MB)','Memory buffer (MB)','Akış işlemede kullanılan tampon sınırıdır; uygulamanın toplam RAM sınırı değildir.','Limits the stream buffer, not total application RAM.'),
('general.proxy','',(), 'Ağ vekili','Network proxy','İsteğe bağlı HTTP veya SOCKS5 adresi. Yalnızca güvendiğin bir vekil kullan.','Optional HTTP or SOCKS5 URL. Use only a proxy you trust.'),
('general.storefront','us',(), 'Varsayılan mağaza','Default storefront','Bağlantıda ülke yoksa kullanılan iki harfli kod: tr, us, gb gibi.','Two-letter fallback when a link has no country, e.g. tr, us, gb.'),
('general.authorization-token','',(), 'API yetkilendirme token’ı','API authorization token','İleri düzey Bearer token. Boş bırakılırsa motor otomatik edinmeye çalışır.','Advanced bearer token. Leave blank for automatic retrieval.'),
('general.exit-on-error',False,(), 'Hatada dur','Stop on error','Açıkken motor hatada çıkar. Kapalıyken uygulama yeniden deneme seçeneği sunar.','When on, the engine exits on error. Otherwise the app offers a retry.'),
('media.get-m3u8-mode','hires',('hires','all'), 'Akış tespit modu','Stream discovery','hires yüksek çözünürlük tespiti; all tüm akışları sorgulamak içindir.','hires detects high-resolution streams; all queries all streams.'),
('media.alac-max',192000,(), 'ALAC üst örnekleme hızı (Hz)','ALAC sample rate cap (Hz)','Örneğin 44100, 48000, 96000 veya 192000. Yüksek sınır kaliteyi garanti etmez.','For example 44100, 48000, 96000 or 192000. A high cap does not guarantee quality.'),
('media.atmos-max',2768,(), 'Atmos bit hızı sınırı','Atmos bitrate cap','Motorun Atmos akışı için üst sınırı; 2448 veya 2768 tipik değerlerdir.','Upper limit for Atmos streams; typical values are 2448 and 2768.'),
('media.aac-type','aac-lc',('aac-lc','aac','aac-binaural','aac-downmix'), 'AAC profili','AAC profile','Yalnızca AAC indirmelerine uygulanır. Kullanılabilir profiller parçaya göre değişir.','Applies only to AAC jobs. Available profiles depend on the track.'),
('media.alac-fix',True,(), 'ALAC paket onarımı','Repair ALAC packets','Bozuk olduğu bilinen ALAC paketlerini düzeltmeye çalışır.','Attempts to patch known malformed ALAC packets.'),
('media.mv.audio-type','atmos',('atmos','ac3','aac'), 'Klip ses biçimi','Music video audio','Müzik klipleri için tercih edilen ses biçimi.','Preferred audio format for music videos.'),
('media.mv.max',2160,(), 'Klip çözünürlük sınırı','Music video resolution cap','Örneğin 720, 1080 veya 2160 satır.','For example 720, 1080 or 2160 lines.'),
('paths.alac','AM-Lossless',(), 'ALAC klasörü','ALAC folder','Mutlak yol veya motor klasörüne göre göreli yol.','Absolute path or a path relative to the engine folder.'),
('paths.atmos','AM-Atmos',(), 'Atmos klasörü','Atmos folder','Atmos indirmelerinin hedefi.','Destination for Atmos downloads.'),
('paths.aac','AM-AAC',(), 'AAC klasörü','AAC folder','AAC indirmelerinin hedefi.','Destination for AAC downloads.'),
('paths.mv','AM-MV',(), 'Klip klasörü','Music video folder','Müzik kliplerinin hedefi.','Destination for music videos.'),
('paths.album-folder','{AlbumName}',(), 'Albüm klasör şablonu','Album folder template','Örnek: {ArtistName} - {AlbumName} [{ReleaseYear}].','Example: {ArtistName} - {AlbumName} [{ReleaseYear}].'),
('paths.playlist-folder','{PlaylistName}',(), 'Liste klasör şablonu','Playlist folder template','Örnek: {PlaylistName} [{PlaylistId}].','Example: {PlaylistName} [{PlaylistId}].'),
('paths.artist-folder','{UrlArtistName}',(), 'Sanatçı klasör şablonu','Artist folder template','{ArtistName}, {ArtistId} ve {UrlArtistName} kullanılabilir. Boş değer alt klasörü kapatır.','Supports {ArtistName}, {ArtistId} and {UrlArtistName}. Leave blank to omit the subfolder.'),
('paths.song-file','{SongNumer}. {SongName}',(), 'Parça dosya şablonu','Track filename template','Motor {SongNumer}, {SongName}, {TrackNumber}, {DiscNumber}, {ArtistName} gibi alanları doldurur.','The engine expands fields such as {SongNumer}, {SongName}, {TrackNumber}, {DiscNumber} and {ArtistName}.'),
('paths.limit-max',200,(), 'Ad uzunluğu sınırı','Name length limit','Klasör ve dosya adları için karakter sınırı.','Character cap for file and folder names.'),
('paths.explicit','[E]',(), 'Sansürsüz içerik etiketi','Explicit tag','Sansürsüz sürümleri işaretler; boş bırakılırsa etiket eklenmez.','Marks explicit versions. Leave blank to omit.'),
('paths.clean','[C]',(), 'Sansürlü içerik etiketi','Clean tag','Düzenlenmiş sürümleri işaretler; boş bırakılırsa etiket eklenmez.','Marks edited versions. Leave blank to omit.'),
('paths.apple-master','[M]',(), 'Apple Digital Master etiketi','Apple Digital Master tag','Apple Digital Master kayıtlarını işaretler; boş bırakılırsa etiket eklenmez.','Marks Apple Digital Master releases. Leave blank to omit.'),
('metadata.lyrics.save-file',False,(), 'Sözleri ayrı kaydet','Save separate lyrics','Şarkı sözleri varsa ses dosyasının yanına kaydeder.','Saves available lyrics next to the audio file.'),
('metadata.lyrics.embed',True,(), 'Sözleri göm','Embed lyrics','Desteklenen ses dosyalarına şarkı sözlerini ekler.','Adds lyrics to supported audio files.'),
('metadata.lyrics.type','lyrics',('lyrics','syllable-lyrics'), 'Söz zamanlaması','Lyric timing','Satır düzeyi ya da mevcutsa hece düzeyi zamanlama.','Line timing or syllable timing when available.'),
('metadata.lyrics.format','lrc',('lrc','ttml'), 'Söz dosya biçimi','Lyrics format','LRC yaygın oynatıcılar için; TTML daha ayrıntılı zamanlama taşıyabilir.','LRC works in many players; TTML can carry richer timing.'),
('metadata.lyrics.extra','',('','translation','pronunciation'), 'Ek söz bilgisi','Extra lyrics','Apple sunuyorsa çeviri ya da telaffuz ekler; boş değer kapatır.','Adds translation or pronunciation if Apple supplies it; blank disables.'),
('metadata.artwork.embed',True,(), 'Kapağı göm','Embed cover','Kapak görselini desteklenen dosyanın içine yazar.','Writes the cover image into supported files.'),
('metadata.artwork.size','5000x5000',(), 'Kapak boyutu','Cover dimensions','Genişlik x yükseklik; örneğin 1400x1400.','Width x height, e.g. 1400x1400.'),
('metadata.artwork.format','jpg',('jpg','png','original'), 'Kapak biçimi','Cover format','JPEG genellikle daha küçük; original mevcut biçimi korur.','JPEG is usually smaller; original preserves the available format.'),
('metadata.artwork.save-artist',False,(), 'Sanatçı görselini kaydet','Save artist artwork','Mevcut sanatçı görselini ayrı dosya olarak saklar.','Saves available artist artwork separately.'),
('metadata.artwork.save-animated',False,(), 'Hareketli kapağı kaydet','Save animated artwork','Hareketli kapak varsa video olarak kaydeder. FFmpeg gerekir.','Saves available motion artwork as video. Requires FFmpeg.'),
('metadata.artwork.emby-animated',False,(), 'Emby/Jellyfin kapağı','Emby/Jellyfin artwork','Hareketli kapağı medya sunucusuna uygun adlandırır. FFmpeg gerekir.','Formats motion artwork for media servers. Requires FFmpeg.'),
('metadata.artwork.dl-for-playlist',False,(), 'Listedeki albüm kapakları','Album art in playlists','Listedeki parçalar için albüm görsellerini ayrıca indirir.','Fetches separate album art for playlist tracks.'),
('metadata.tags.sort-order',True,(), 'Sıralama etiketleri','Sort tags','Müzik kütüphaneleri için sıralama alanları ekler.','Adds sort fields for music libraries.'),
('metadata.tags.itunes-id',True,(), 'iTunes kimlikleri','iTunes IDs','Katalog kimliklerini dosya meta verisine yazar.','Writes catalog identifiers into file metadata.'),
('metadata.tags.use-songinfo-for-playlist',False,(), 'Listede özgün etiketler','Original tags in playlists','Liste sırası yerine orijinal albüm, disk ve parça bilgisini kullanır.','Uses original album, disc and track metadata instead of playlist ordering.'),
('convert.after-download',False,(), 'Dönüştürmeyi aç','Enable conversion','İndirme bitince FFmpeg ile dönüştürür.','Transcodes with FFmpeg after download.'),
('convert.format','flac',('flac','mp3','opus','wav','copy'), 'Hedef biçim','Target format','copy yeniden kodlama yapmadan akışı kopyalamayı dener.','copy attempts to copy the stream without re-encoding.'),
('convert.keep-original',False,(), 'Orijinali koru','Keep original','Dönüştürme başarılı olunca kaynak dosyayı silmez.','Keeps the source after successful conversion.'),
('convert.skip-if-source-matches',True,(), 'Biçim eşleşirse atla','Skip matching formats','Kaynak zaten hedef biçimdeyse gereksiz dönüşümü önler.','Avoids unnecessary conversion when the source already matches.'),
('convert.ffmpeg-path','ffmpeg',(), 'FFmpeg çalıştırılabilir dosyası','FFmpeg executable','PATH üzerinde ffmpeg veya güvendiğin bir mutlak dosya yolu.','Use ffmpeg on PATH or a trusted absolute executable path.'),
('convert.extra-args','',(), 'Ek FFmpeg seçenekleri','Extra FFmpeg arguments','İleri düzey: Örneğin -b:a 192k. Seçenekler doğrudan FFmpeg’e iletilir.','Advanced: e.g. -b:a 192k. Arguments are passed to FFmpeg.'),
('convert.with-metadata',True,(), 'Meta veriyi taşı','Preserve metadata','Desteklenen etiketleri dönüştürülen dosyaya taşır.','Carries supported tags to the converted output.'),
('convert.warn-lossy-to-lossless',True,(), 'Kayıplıdan kayıpsıza uyar','Warn on lossy to lossless','Dönüştürmenin kaybolmuş ses ayrıntılarını geri getirmediğini hatırlatır.','Warns that conversion cannot restore lost audio detail.'),
('convert.skip-lossy-to-lossless',True,(), 'Kayıplıdan kayıpsıza atla','Skip lossy to lossless','Kayıplı kaynağı FLAC veya WAV gibi hedeflere dönüştürmez.','Skips converting lossy sources to formats such as FLAC or WAV.'),
('convert.check-bad-alac',False,(), 'Bozuk ALAC denetimi','Check damaged ALAC','ALAC akışındaki bozuklukları denetleyip raporlar.','Checks and reports damage in ALAC audio.'),
('convert.delete-bad-alac',False,(), 'Bozuk ALAC dosyasını sil','Delete damaged ALAC','Dikkat: Motorun bozuk olarak saptadığı ALAC dosyalarını silebilir.','Caution: can delete ALAC files that the engine detects as damaged.'),
]

SECRET = {'general.media-user-token', 'general.authorization-token', 'general.proxy'}


def get(data, path, default=None):
    for key in path.split('.'):
        if not isinstance(data, dict) or key not in data:
            return default
        data = data[key]
    return data if data is not None else default


def put(data, path, value):
    *parents, key = path.split('.')
    for part in parents:
        if not isinstance(data.get(part), dict):
            data[part] = {}
        data = data[part]
    data[key] = value
