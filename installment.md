# Panduan Instalasi & Menjalankan Screen Layer

Panduan lengkap dari memasang webcam sampai membuka aplikasi di setiap HP/tablet.

---

## Daftar isi
1. [Yang dibutuhkan](#1-yang-dibutuhkan)
2. [Install di laptop](#2-install-di-laptop)
3. [Pasang kamera](#3-pasang-kamera)
4. [Pasang marker di sudut meja](#4-pasang-marker-di-sudut-meja)
5. [Jalankan server](#5-jalankan-server)
6. [Buka panel kontrol di laptop](#6-buka-panel-kontrol-di-laptop)
7. [Buka app di setiap HP/tablet](#7-buka-app-di-setiap-hptablet)
8. [Kalibrasi dan putar video](#8-kalibrasi-dan-putar-video)
9. [Kalau ada masalah](#9-kalau-ada-masalah)

---

## 1. Yang dibutuhkan

| Perangkat | Keterangan |
|---|---|
| Laptop/PC | Windows, Mac, atau Linux dengan **Python 3.9+**. Laptop ini menjadi server. |
| Kamera | Webcam USB atau HP bekas sebagai kamera. Harus bisa melihat seluruh meja dari atas. |
| HP/tablet | Sebanyak yang mau dipakai. Browser Safari (iOS) atau Chrome (Android). |
| Wi-Fi | **Semua perangkat harus di jaringan Wi-Fi yang sama.** Jangan pakai Wi-Fi tamu. |
| Printer | Untuk mencetak 4 marker sudut meja. Kalau tidak ada printer, marker bisa ditampilkan di 4 HP lain. |

---

## 2. Install di laptop

```bash
git clone https://github.com/aidevvirtual-crypto/screen-layer
cd screen-layer

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Taruh video yang mau diputar di folder `screen-layer`, misalnya `video.mp4`.

> Di Windows, pakai `python` sebagai pengganti `python3`.

---

## 3. Pasang kamera

Pasang kamera **menghadap lurus ke bawah**, sekitar **60–100 cm** di atas meja. Pakai tripod, lengan lampu, atau tempelkan di rak. Pastikan seluruh area meja masuk dalam gambar.

### Pilihan A: webcam USB
- Colokkan webcam ke laptop.
- Nomor kameranya biasanya `0`. Kalau laptop punya kamera bawaan, webcam USB biasanya `1`.

### Pilihan B: HP Android sebagai kamera
1. Install app **"IP Webcam"** dari Play Store.
2. Buka app tersebut, scroll ke bawah, lalu tekan **Start server**.
3. Catat alamat yang muncul di layar, misalnya `http://192.168.1.50:8080`.
4. Alamat kamera yang dipakai nanti adalah alamat itu ditambah `/video`:
   `http://192.168.1.50:8080/video`
5. Cek dulu dengan membuka alamat tersebut di browser laptop. Kalau gambar kamera muncul, berarti sudah benar.

### Pilihan C: iPhone + Mac
- Pakai **Continuity Camera**. iPhone akan muncul sebagai webcam biasa dengan nomor `0` atau `1`.

### Tips kamera
- Hindari pantulan lampu langsung di layar HP.
- Nyalakan lampu ruangan secukupnya, jangan terlalu gelap.
- Semakin tegak lurus ke bawah posisi kamera, semakin akurat hasilnya.

---

## 4. Pasang marker di sudut meja

1. Jalankan server sebentar (lihat [langkah 5](#5-jalankan-server)), lalu buka `http://IP-LAPTOP:8000/markers` di laptop dan **cetak** halamannya.
2. Gunting keempat marker, lalu letakkan **menghadap ke atas** di sudut area meja:

   ```
   ┌───────────────────────────┐
   │ [0]                   [1] │   0 = kiri-atas
   │                           │   1 = kanan-atas
   │        area meja          │   2 = kanan-bawah
   │                           │   3 = kiri-bawah
   │ [3]                   [2] │
   └───────────────────────────┘
        (dilihat dari kamera)
   ```

3. **Ukur jarak antar TITIK TENGAH marker** dalam cm:
   - Lebar = jarak dari tengah marker 0 ke tengah marker 1
   - Tinggi = jarak dari tengah marker 0 ke tengah marker 3

   Contoh: lebar 60 cm dan tinggi 40 cm → `--table 60x40`

---

## 5. Jalankan server

```bash
# webcam USB:
python3 server.py --video video.mp4 --camera 0 --table 60x40 --https

# HP Android sebagai kamera:
python3 server.py --video video.mp4 --camera http://192.168.1.50:8080/video --table 60x40 --https

# tanpa kamera (posisi layar diatur manual dengan mouse):
python3 server.py --video video.mp4
```

Server akan menampilkan alamatnya:

```
  video   : video.mp4
  screens : https://192.168.1.10:8000/
  control : https://192.168.1.10:8000/control
  markers : https://192.168.1.10:8000/markers
  mode    : camera 0
```

### Opsi server

| Opsi | Fungsi | Default |
|---|---|---|
| `--video` | File video yang diputar | file `*.mp4` pertama di folder |
| `--camera` | Nomor kamera (`0`, `1`) atau URL stream | tanpa kamera (mode manual) |
| `--table` | Ukuran area meja `LEBARxTINGGI` dalam cm | `60x40` |
| `--port` | Port server | `8000` |
| `--https` | Pakai HTTPS (sertifikat self-signed dibuat otomatis) | mati |

> **Kenapa `--https`?** HP hanya mengizinkan sensor gerak lewat HTTPS. Dengan HTTPS, marker muncul otomatis saat HP digerakkan, layar tidak mati sendiri, dan mode fullscreen bisa dipakai.

### Firewall
Izinkan Python atau port 8000 supaya HP bisa terhubung ke laptop:
- **Windows:** pilih **Allow access** saat muncul pop-up firewall.
- **Mac:** pilih **Allow** saat ditanya "accept incoming network connections".
- **Linux:** `sudo ufw allow 8000`

---

## 6. Buka panel kontrol di laptop

1. Buka alamat **control** di browser laptop, misalnya `https://192.168.1.10:8000/control`.
2. Kalau muncul peringatan sertifikat, pilih **Advanced → Proceed**.
3. Di bagian **Tracking** akan terlihat preview kamera.
4. Tunggu sampai muncul tulisan **"meja terkalibrasi ✓"**.
5. Setelah itu keempat marker sudut **boleh diambil**, karena kalibrasinya tersimpan sampai server dimatikan. Kalau kamera bergeser, letakkan lagi markernya.

---

## 7. Buka app di setiap HP/tablet

Lakukan langkah ini **di setiap perangkat**.

### a. Atur HP dulu
- Kecerahan layar **maksimal**
- **Kunci rotasi layar**
- Matikan auto-lock:
  - iPhone/iPad: *Settings → Display & Brightness → Auto-Lock → Never*
  - Android: *Pengaturan → Layar → Waktu tunggu layar → paling lama*

### b. Buka alamat screens
Buka alamat **screens**, misalnya `https://192.168.1.10:8000/`, di:
- **Safari** untuk iPhone/iPad
- **Chrome** untuk Android

### c. Terima peringatan sertifikat (kalau pakai `--https`)
- **iPhone/iPad:** *Show Details → visit this website → Visit Website*
- **Android:** *Lanjutan → Lanjutkan ke situs (tidak aman)*

### d. Gabung
1. Tekan tombol **Gabung**.
2. Di iPhone/iPad, pilih **Allow** saat diminta akses *Motion & Orientation*.
3. Di pojok kiri atas layar akan terlihat nomor perangkat, misalnya `#10`.

### e. Letakkan di meja dan lacak posisinya
1. Letakkan perangkat di meja dengan layar menghadap kamera.
2. **Ketuk dua kali** layar. Marker hitam-putih akan muncul, lalu kamera mengukur posisi, sudut, dan ukuran layar.
3. **Ketuk dua kali lagi** untuk kembali ke video.

> Kalau server memakai `--https`, cukup **geser HP-nya**. Marker muncul sendiri dan hilang sekitar 1 detik setelah HP diam.

### f. (Opsional) Pengaturan ⚙
Tombol ⚙ ada di pojok kanan atas layar:
- **Lebar layar fisik (cm):** isi kalau tidak memakai kamera, supaya ukuran potongan video pas. Kosongkan kalau memakai kamera (ukuran diukur otomatis).
- **Suara:** centang di **satu perangkat saja**.

---

## 8. Kalibrasi dan putar video

1. Di panel kontrol, centang **Grid kalibrasi**.
   Kalau garis diagonal putih terlihat **menyambung lurus** melewati semua layar, kalibrasi sudah pas.
2. Tekan **"Pas ke meja"** supaya video muat di area meja.
3. Atur posisi video kalau perlu:
   - **Geser** video di kanvas panel kontrol
   - Slider **Lebar** untuk memperbesar/memperkecil
   - Slider **Rotasi** untuk memutar
4. Matikan grid, lalu tekan **▶ Putar**. Semua layar akan memutar video yang sama secara serempak.

### Mode tanpa kamera
Kalau server dijalankan tanpa `--camera`:
- Geser kotak layar `#10`, `#11`, dst. di panel kontrol sesuai posisi HP di meja.
- Putar dengan **scroll mouse**, tombol **Q/E**, atau slider **Rotasi** di bagian "Terpilih".

---

## 9. Kalau ada masalah

| Gejala | Solusi |
|---|---|
| HP tidak bisa membuka alamat server | Pastikan Wi-Fi-nya sama, izinkan firewall, dan jangan pakai Wi-Fi tamu (biasanya antar perangkat diblokir) |
| `cannot open camera` | Coba `--camera 1` atau `2`. Untuk IP Webcam, buka URL-nya di browser laptop dulu untuk memastikan kameranya jalan |
| "Meja BELUM terkalibrasi" | Keempat marker 0–3 harus terlihat **bersamaan** di preview kamera |
| Marker HP tidak terbaca | Naikkan kecerahan layar, kurangi pantulan lampu, atau dekatkan kamera |
| Gambar antar layar tidak menyambung | Ulangi ketuk dua kali di HP itu, dan cek angka `--table` sudah sesuai jarak antar titik tengah marker |
| Ukuran potongan video tidak pas (tanpa kamera) | Isi lebar layar fisik (cm) lewat tombol ⚙ di HP |
| Video tidak berputar di HP | Tekan **Gabung**, karena browser tidak mengizinkan video berputar otomatis tanpa sentuhan |
| Marker tidak muncul otomatis saat HP digerakkan | Jalankan server dengan `--https`, dan izinkan akses Motion di iPhone |
| Layar HP mati sendiri | Matikan auto-lock (lihat [langkah 7a](#a-atur-hp-dulu)) |
| Video portrait terlalu tinggi untuk meja | Tekan **"Pas ke meja"** di panel kontrol |
