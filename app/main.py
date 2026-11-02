from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .db import get_conn, hitung_saldo, init_db

app = FastAPI(title="Pencatat Keuangan")
init_db()


class AkunIn(BaseModel):
    nama: str
    tipe: Literal["bank", "ewallet", "tunai"] = "bank"
    saldo_awal: int = 0


class TransaksiIn(BaseModel):
    tipe: Literal["pemasukan", "pengeluaran", "transfer"]
    nominal: int = Field(gt=0)
    akun: str                           # nama akun sumber, misal "BCA"
    akun_tujuan: Optional[str] = None   # khusus transfer
    kategori: Optional[str] = None
    catatan: Optional[str] = None


def cari_akun_id(conn, nama: str) -> int:
    row = conn.execute(
        "SELECT id FROM accounts WHERE lower(nama) = lower(?)", (nama,)
    ).fetchone()
    if not row:
        raise HTTPException(404, f"Akun '{nama}' tidak ditemukan")
    return row["id"]


@app.post("/akun")
def buat_akun(a: AkunIn):
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO accounts (nama, tipe, saldo_awal) VALUES (?,?,?)",
                (a.nama, a.tipe, a.saldo_awal),
            )
        except Exception:
            raise HTTPException(400, "Nama akun sudah ada")
    return {"ok": True}


@app.get("/akun")
def daftar_akun():
    akun = hitung_saldo()
    return {"akun": akun, "total": sum(x["saldo"] for x in akun)}


@app.post("/transaksi")
def tambah_transaksi(t: TransaksiIn):
    with get_conn() as conn:
        sumber = cari_akun_id(conn, t.akun)
        tujuan = None
        if t.tipe == "transfer":
            if not t.akun_tujuan:
                raise HTTPException(400, "Transfer butuh akun_tujuan")
            tujuan = cari_akun_id(conn, t.akun_tujuan)
        conn.execute(
            """INSERT INTO transactions
               (tipe, nominal, kategori, catatan, account_id, to_account_id)
               VALUES (?,?,?,?,?,?)""",
            (t.tipe, t.nominal, t.kategori, t.catatan, sumber, tujuan),
        )
    return {"ok": True, "saldo": hitung_saldo()}


@app.get("/transaksi")
def riwayat(limit: int = 50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]