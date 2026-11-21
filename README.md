# Screen Layer

Satu video "ditempel" di permukaan meja. Setiap HP/tablet yang diletakkan di atas meja hanya menampilkan
potongan video yang ada tepat di bawahnya (posisi, rotasi, dan skala ikut menyesuaikan). Posisi layar
dilacak kamera lewat marker ArUco, atau diatur manual dari panel kontrol.

> 📘 Panduan lengkap langkah demi langkah (setup webcam sampai membuka app di tiap perangkat): **[installment.md](installment.md)**

## Jalankan
```bash
pip install -r requirements.txt
python3 server.py --video VID-20261121-WA0001.mp4                         # mode manual (tanpa kamera)
python3 server.py --camera 0 --table 60x40                                # webcam USB
python3 server.py --camera http://IP-HP:8080/video --table 60x40 --https  # HP sebagai IP cam (app "IP Webcam")
```
Server menampilkan alamat yang perlu dibuka:
- `http://IP:8000/` dibuka di setiap HP/tablet (semua harus di Wi-Fi yang sama), lalu tekan **Gabung**
- `http://IP:8000/control` dibuka di laptop: play/pause, seek, posisi/ukuran/rotasi video, grid kalibrasi, preview kamera
- `http://IP:8000/markers` untuk mencetak marker sudut meja (ID 0–3)

## Kalibrasi kamera
1. Kamera menghadap ke bawah, melihat seluruh area meja.
2. Letakkan marker 0 (kiri-atas), 1 (kanan-atas), 2 (kanan-bawah), dan 3 (kiri-bawah). Ukur jarak antar titik tengahnya, lalu isi `--table LxT` (cm).
   Setelah keempat marker terlihat sekali, kalibrasi tersimpan sampai server dimatikan, jadi marker boleh diambil lagi.
3. Di tiap HP: ketuk dua kali untuk menampilkan marker. Kamera akan mengukur posisi, rotasi, **dan ukuran fisik layar** secara otomatis.
   Dengan `--https`, marker juga muncul otomatis saat HP digerakkan dan hilang 1,2 detik setelah HP diam.
4. Nyalakan "Grid kalibrasi" di panel kontrol. Kalau garis diagonal tetap lurus melewati semua layar, berarti kalibrasi sudah pas.

## Cara kerja
- `tracker.py`: OpenCV mendeteksi ArUco → homography kamera→meja (cm) → pose tiap layar `{x, y, sudut}` + cm/px.
- `server.py`: aiohttp; menyimpan state (pose, posisi video, jam playback) dan mengirimnya lewat WebSocket 30 Hz.
- `static/screen.html`: menggambar video di canvas dengan transform `p = R(-a)·(T − C) / k`, jadi tiap layar otomatis menampilkan slice miliknya.
- Sinkronisasi: setiap perangkat memutar file yang sama secara lokal, lalu dikunci ke jam server (sinkron jam ala NTP,
  koreksi `playbackRate` untuk selisih kecil, seek untuk selisih besar).

## Catatan
- Sensor gerak, wake lock, dan fullscreen di iOS/Android hanya aktif lewat HTTPS (`--https`, sertifikat self-signed: terima peringatan di browser).
- Video baru berputar di HP setelah tombol **Gabung** ditekan (aturan autoplay browser). Default tanpa suara; suara bisa diaktifkan di ⚙.
- Kalau tidak ada kamera, ukuran layar bisa diisi manual di ⚙ (lebar layar dalam cm).
- Video portrait (9:16) lebih tinggi dari meja; tekan "Pas ke meja" di panel kontrol.
