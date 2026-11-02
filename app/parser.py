import re

SATUAN = {"rb": 1_000, "ribu": 1_000, "k": 1_000, "jt": 1_000_000, "juta": 1_000_000}

SLANG = {
    "seceng": 1_000, "gopek": 500, "goceng": 5_000, "ceban": 10_000,
    "noban": 20_000, "goban": 50_000, "cepek": 100_000,
    "seribu": 1_000, "sejuta": 1_000_000,
}

# alias -> nama akun (huruf kecil). Dipakai hanya kalau akun tujuannya ada.
ALIAS = {"cash": "tunai", "kas": "tunai", "dompet": "tunai"}

KATA_TRANSFER = r"\b(transfer|tf|pindah|pindahin)\b"
KATA_MASUK = (
    r"\b(gaji|gajian|masuk|terima|diterima|dapat|dapet|bonus|thr|komisi|"
    r"cashback|refund|pemasukan|income|dikasih|untung)\b"
)

# Urutan penting: yang pertama cocok dipakai.
KATEGORI = [
    ("Tagihan", ["listrik", "wifi", "internet", "pulsa", "token", "cicilan",
                 "kontrakan", "kos", "sewa", "bpjs", "pajak", "pdam", "tagihan"]),
    ("Transport", ["bensin", "pertamax", "parkir", "tol", "ojek", "grab", "bus",
                   "krl", "kereta", "angkot", "transport", "taksi"]),
    ("Makan", ["makan", "sarapan", "kopi", "minum", "jajan", "snack", "bakso",
               "nasi", "ayam", "resto", "cafe", "warteg", "gofood", "grabfood"]),
    ("Kesehatan", ["obat", "dokter", "apotek", "klinik"]),
    ("Hiburan", ["nonton", "bioskop", "game", "netflix", "spotify", "liburan"]),
    ("Gaji", ["gaji", "gajian"]),
    ("Bonus", ["bonus", "thr"]),
    ("Belanja", ["belanja", "beli", "shopee", "tokopedia", "baju", "sepatu",
                 "indomaret", "alfamart"]),
]


def cari_nominal(t: str):
    # 1. angka + satuan: 25rb, 1,5jt, 2k
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(rb|ribu|jt|juta|k)\b", t)
    if m:
        angka = float(m.group(1).replace(",", "."))
        return int(round(angka * SATUAN[m.group(2)]))
    # 2. angka dengan pemisah ribuan: 25.000 atau 1.500.000
    m = re.search(r"\d{1,3}(?:[.,]\d{3})+(?!\d)", t)
    if m:
        return int(re.sub(r"[.,]", "", m.group()))
    # 3. kata gaul: goceng, ceban, dst.
    for kata, nilai in SLANG.items():
        if re.search(rf"\b{kata}\b", t):
            return nilai
    # 4. angka polos: 25000
    m = re.search(r"\d+", t)
    if m:
        return int(m.group())
    return None


def cari_akun(t: str, daftar_akun: list):
    kandidat = {nama.lower(): nama for nama in daftar_akun}
    for alias, target in ALIAS.items():
        if target in kandidat:
            kandidat.setdefault(alias, kandidat[target])

    ditemukan = []
    for kata, nama in kandidat.items():
        for m in re.finditer(rf"\b{re.escape(kata)}\b", t):
            ditemukan.append((m.start(), nama))
    ditemukan.sort()

    unik = []
    for pos, nama in ditemukan:
        if nama not in [n for _, n in unik]:
            unik.append((pos, nama))
    return unik


def cari_kategori(t: str, tipe: str):
    if tipe == "transfer":
        return "Transfer"
    for nama, kata_kunci in KATEGORI:
        for kata in kata_kunci:
            if re.search(rf"\b{kata}\b", t):
                return nama
    return "Lainnya"


def parse_pesan(teks: str, daftar_akun: list) -> dict:
    t = teks.lower().strip()

    nominal = cari_nominal(t)
    if not nominal:
        return {"error": "Nominal tidak ditemukan. Contoh: 'makan siang 25rb pakai bca'"}

    akun_list = cari_akun(t, daftar_akun)

    # Tentukan tipe transaksi
    if re.search(KATA_TRANSFER, t) and len(akun_list) >= 2:
        tipe = "transfer"
    elif re.search(KATA_MASUK, t):
        tipe = "pemasukan"
    elif re.search(KATA_TRANSFER, t):
        return {"error": "Transfer butuh dua akun. Contoh: 'transfer 100rb dari bca ke gopay'"}
    else:
        tipe = "pengeluaran"

    sumber = tujuan = None

    if tipe == "transfer":
        # Cari penanda "dari X" dan "ke Y"
        for pos, nama in akun_list:
            sebelum = t[:pos].rstrip()
            if re.search(r"\bdari$", sebelum) and not sumber:
                sumber = nama
            elif re.search(r"\bke$", sebelum) and not tujuan:
                tujuan = nama
        # Kalau tidak ada penanda, pakai urutan kemunculan
        sisa = [n for _, n in akun_list if n not in (sumber, tujuan)]
        if not sumber and sisa:
            sumber = sisa.pop(0)
        if not tujuan and sisa:
            tujuan = sisa.pop(0)
        if not (sumber and tujuan):
            return {"error": "Akun transfer tidak jelas. Contoh: 'transfer 100rb dari bca ke gopay'"}
    else:
        sumber = akun_list[0][1] if akun_list else None

    return {
        "tipe": tipe,
        "nominal": nominal,
        "akun": sumber,
        "akun_tujuan": tujuan,
        "kategori": cari_kategori(t, tipe),
        "catatan": teks.strip(),
    }