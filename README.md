


# WSN Earthquake Early Warning Simulation (Tkinter)

Bu proje, Kablosuz Sensör Ağları (Wireless Sensor Networks - WSN) kullanılarak tasarlanmış bir **Deprem Erken Uyarı Sistemi** simülasyonudur. Projenin amacı, sismik dalgaların yayılımını, sensörlerin algılama anını ve verilerin merkez düğüme (Gateway) nasıl iletildiğini görsel ve interaktif bir şekilde açıklamaktır. Python ve Tkinter kütüphanesi kullanılarak geliştirilmiştir.

## 📖 Eğitim ve Simülasyon Hedefleri

Simülasyon, ağ sistemlerinin temel mantığını anlamak için aşağıdaki adımları görsel olarak sunar:

1. **Uyku Modu (Sleep State):** Enerji tasarrufu amacıyla sensörlerin sismik aktivite olana kadar beklemesi.
2. **P-Dalgası Yayılımı:** Yıkıcı S-dalgalarından önce gelen ve hızlı yayılan P-dalgalarının (6000 m/s) sensörleri uyandırması.
3. **Multi-Hop İletim (Atlamalı):** Sensörlerin Dijkstra algoritmasına benzer mantıkla, elde ettikleri verileri komşular üzerinden atlatarak en kısa yoldan merkeze ulaştırması.
4. **Veri Füzyonu ve Quorum Mantığı:** Yanlış alarmları önlemek için merkezin en az $K$ sayıda (Quorum) farklı sensörden onay beklemesi ve bu şart sağlandığında alarm üretmesi.

## ✨ Temel Özellikler

* **İnteraktif Arayüz:** Kullanıcı tarafından seçilebilen farklı deprem senaryoları (Örn: Seydişehir Merkez M5.0, Beyşehir Sınırı M4.2).
* **Görsel Gerçek Zamanlı Geri Bildirim:** Dalgaya maruz kalan sensörlerin renk değiştirmesi ve veri aktarım yollarının dinamik çizimi.
* **Bilgilendirici Yan Panel:** Simülasyon sırasında olan biteni adımlar halinde açıklayan eğitici rehber alanı ve anlık istatistikler.
* **Kurulum Gerektirmeyen Yapı:** Python'ın standart `tkinter` kütüphanesi ile dışa bağımlılık olmadan çalışma imkanı.

## 🛠️ Kurulum ve Çalıştırma

Projenin çalışması için bilgisayarınızda Python 3.x yüklü olması yeterlidir.

1. Depoyu bilgisayarınıza klonlayın:
```bash
git clone https://github.com/KULLANICI_ADINIZ/PROJE_DEPOSU.git
cd PROJE_DEPOSU

```


2. Simülasyon betiğini çalıştırın:
```bash
python3 wsn_tkinter_sim.py

```


*(Eğer Windows kullanıyorsanız `python wsn_tkinter_sim.py` olarak çalıştırabilirsiniz.)*

## 🎯 Nasıl Kullanılır?

1. Uygulama açıldığında sol panelde düğümlerden oluşan kablosuz ağ topolojisi görünecektir.
2. Sağ panelde yer alan senaryolardan birine tıklayarak deprem olayını tetikleyin.
3. Sismik dalga çapının genişleyişini izleyin. Dalganın ulaştığı düğümler sarı renge dönüşecektir.
4. Dalga yayıldıktan sonra verilerin *Gateway* (Merkez) noktasına aktarımını ve onay durumunu ekran üzerinden takip edin. Sağ alt köşedeki "Sıfırla" butonu ile simülasyonu başa alabilirsiniz.

## 🤝 Katkıda Bulunma

Eğer simülasyona yeni ağ algoritmaları (örn. LEACH protokolü), enerji tüketim metrikleri veya farklı topolojiler eklemek isterseniz, lütfen bir "Pull Request" oluşturun. Katkılarınız değerlidir!
