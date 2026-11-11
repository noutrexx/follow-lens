# Kullanım kılavuzu

FollowLens Instagram ile nasıl konuşur, bunun maliyeti nedir ve hesabın kısıtlanmadan nasıl kullanılır.

English: [USAGE.md](USAGE.md)

## Kısa hali

- Günde **bir ya da iki kez** tara. Daha sık taramak yeni bir şey göstermez, sadece riski artırır.
- **Birkaç hesap** izle, onlarca değil.
- Bekleme süresine dokunma. `?force=1` kullanmayı alışkanlık yapma.
- Instagram bir uyarı gösterirse ya da tarama hız sınırı bildirirse **en az bir gün dur**.
- Mümkünse ana hesabının değil, **ikinci bir hesabın** oturumunu kullan.

## Bir tarama gerçekte ne gönderir

FollowLens'in API anahtarı ya da özel bir erişimi yoktur. Birinin takipçi listesini açtığında tarayıcının gönderdiği web isteklerinin aynısını, senin verdiğin oturum çereziyle gönderir. Başka hiçbir yere bağlanmaz.

İzlenen her hesap için bir tarama şunları yapar:

| Adım | İstek |
| --- | --- |
| Hesap kimliğini bulma | İlk seferde 1, sonra 0 (kimlik `known_ids` içine kaydedilir) |
| **Takip edilenleri** okuma | Her geçişte, 200 hesap başına 1 istek |
| **Takipçileri** okuma | Her geçişte, 100 hesap başına 1 istek |

Her liste **2 ila 4 geçişte** okunur. Instagram'ın listeleri güvenilir değildir: tek geçiş düzenli olarak bazı hesapları atlar. FollowLens okumayı tekrarlayıp sonuçları birleştirir ve bir geçiş yeni kimseyi eklemediği anda durur. Yani oturmuş bir liste iki geçişe, kararsız bir liste en fazla `followers_max_passes` geçişe mal olur.

Hesap başına, tarama başına toplam:

| Hesap büyüklüğü (takip / takipçi) | İstek | Süre |
| --- | --- | --- |
| yaklaşık 180 / 180 | 6 – 12 | bir dakikadan az |
| 500 / 500 | 16 – 32 | 1 – 3 dakika |
| 1.000 / 2.000 | 50 – 100 | 3 – 9 dakika |
| 800 / 5.000 | desteklenmiyor, bkz. [Sınırlar](#sınırlar) | |

Bunu izlediğin hesap sayısıyla çarp. Üç küçük hesap, tarama başına kabaca 20 – 35 istek eder.

## İstekler nasıl aralanır

| Ayar | Varsayılan | Ne yapar |
| --- | --- | --- |
| `delay_seconds` | 3.0 | Her istekten sonra bekleme |
| `delay_jitter_seconds` | 2.5 | Üstüne eklenen rastgele bekleme; istekler sabit bir ritimle değil, 3,0 – 5,5 sn arayla gider |
| `min_scan_interval_seconds` | 600 | İki tarama arasındaki en kısa süre |
| `followers_max_passes` | 4 | Liste başına en fazla geçiş sayısı |

Instagram `429 Too Many Requests` dönerse FollowLens önce yaklaşık 15, sonra yaklaşık 30 saniye bekler; yine olmazsa zorlamak yerine taramanın tamamından vazgeçer.

Bekleme süresiyle ilgili iki kural:

- **Hiçbir şey okuyamayan** tarama (süresi dolmuş oturum, bağlantı yok) bekleme süresini başlatmaz; sebebi düzeltir düzeltmez yeniden deneyebilirsin.
- **Yeni eklenen bir hesabın ilk okuması** bir kereliğine beklemeye takılmaz. Sonraki her tarama bekler.

## Risk, açıkça

Bu listeleri otomatik okumak Instagram'ın Kullanım Koşulları'na aykırıdır. Instagram sınırlarını yayımlamaz ve haber vermeden değiştirir; bu yüzden **kimse sana güvenli bir sayı garanti edemez**, bu kılavuz da edemez. Aşağıdakiler garanti değil, istek hacmini düşük tutmanın yoludur.

Instagram'ın yapabilecekleri, kabaca hafiften ağıra:

1. **Tek bir hesabın listelerini** bir süre vermez. Tarama *"The session itself works … Instagram is refusing this account for now."* der.
2. **Oturuma hız sınırı** koyar; 429 ile ya da sessizce *"Please wait a few minutes."* diyerek.
3. **Oturumu kapatır.** Tüm hesaplar başarısız olur, yeni çerez gerekir.
4. **Uygulamada uyarı gösterir** (otomatik davranış) ya da kimliğini doğrulamanı ister.
5. **Hesabı kısıtlar ya da kapatır.** Bu hacimlerde nadirdir, ama yukarıdaki her şeyin sebebi budur.

Riski artıranlar:

- Günde çok kez taramak ya da `?force=1` ile döngüye sokmak
- Çok sayıda ya da çok büyük hesap izlemek
- Beklemeleri kısaltmak
- Aynı hesapla uygulamada çok aktifken tarama çalıştırmak
- Bir uyarıdan sonra devam etmek

## Bir şeyler ters giderse

| Gördüğün | Yapman gereken |
| --- | --- |
| Bir hesap reddedildi, diğerleri sorunsuz | Birkaç saat bekle. Yeni çerez **alma**; oturum sağlam. |
| 429 ya da *"Please wait a few minutes"* | En az 30 dakika dur. Aynı gün tekrar olursa yarına kadar dur. |
| Tüm hesaplar 401 ile başarısız | Oturumun süresi dolmuş. `config.json` içine yeni `sessionid` yapıştır. |
| Instagram içinde bir uyarı | 24 – 48 saat tarama yapma. Döndüğünde sıklığı yarıya indir. |
| Kimlik doğrulama isteği | Uygulamada tamamla, sonra taramaya dönmeden önce birkaç gün bekle. |

Mesajların tam listesi [README](../README.md#troubleshooting) içinde.

## Oturum çerezi

`sessionid` çerezi senin girişinin **ta kendisidir**. Onu ele geçiren, şifren olmadan hesabını kullanabilir.

- Yalnızca git tarafından yok sayılan `config.json` içinde durur. Asla commit'leme, bir sohbete yapıştırma ya da ekran görüntüsüne sokma.
- Yalnızca `instagram.com`'a gönderilir.
- Birkaç günle birkaç hafta arasında dayanır. Süresi dolunca tarayıcından yenisini kopyala.
- Hemen iptal etmek için Instagram'da o tarayıcı oturumundan çıkış yap. Şifreni değiştirmek hepsini iptal eder.

İkinci bir hesabın oturumunu kullanmak ana hesabını işin tamamen dışında tutar. Bedeli: yalnızca o ikinci hesabın görebildiklerini okuyabilirsin.

## FollowLens neleri okuyabilir

- **Herkese açık hesaplar**: evet.
- **Gizli hesaplar**: yalnızca oturumun sahibi olan hesap onları takip ediyorsa. Aksi halde FollowLens bunu söyler ve hiçbir şey kaydetmez.
- **Kendi hesabın** (`self` hedefi): her zaman.

Instagram sana göstermeyeceği bir hesap için hata değil, *boş liste* döner. FollowLens önce profilin kendi sayılarına bakar ve takipçisi olduğu belli olan bir hesap için asla boş liste kaydetmez.

## Sınırlar

- **Hesap başına yaklaşık 4.000 takipçi ve 8.000 takip.** Bir okuma 40 sayfadan sonra durur; daha büyük listeler eksik gelir ve fark güvenilir olmaz. FollowLens kişisel ölçekteki hesaplar için yapılmıştır.
- **Zaman bilgisi yok.** Instagram birinin ne zaman takip ettiğini ya da bıraktığını söylemez. "Yeni" her zaman "bir önceki taramadan beri" demektir.
- **Arka planda tarama yok.** Tarama, Yenile'ye bastığında ya da `/scan` çağırdığında çalışır. Kendi kendine hiçbir şey çalışmaz.

## Sonucu okumak

Listeler güvenilir olmadığı için her değişiklik gerçek değildir. Yalnızca düz yeşil ve düz kırmızı satırlar gerçek hareketi gösterir:

| Satır | Anlamı |
| --- | --- |
| `+` yeşil, *yeni takipçi* | Gerçekten yeni biri |
| `+` sönük, *geri geldi* | Daha önce gitmiş görünüyordu, geri döndü; yeni değil |
| `-` kırmızı, *takipten çıktı* | Gitti ve geri gelmedi |
| `-` üstü çizili, *geri döndü* | Sonraki bir tarama onu yine buldu; hiç gitmemişti |
| `~` sönük, *hesap kayıp* | İki listeden aynı anda kayboldu: kapatılmış, adı değişmiş ya da gizliye alınmış |

Aynı isimler sürekli gidip geliyorsa `followers_max_passes` değerini bir artır. Tarama başına birkaç istek daha harcar, ama listeler daha eksiksiz olur.
