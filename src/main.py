import os
import random
import sys
import time
from pathlib import Path
from faker import Faker
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


# ============================================================================
# FUNGSI HELPER UNTUK KONFIGURASI ENVIRONMENT
# ============================================================================

def load_env_file() -> None:
    """Muat file .env dan set variabel environment dari file tersebut.
    
    Membaca file .env di direktori parent dan mengisi os.environ
    dengan values yang ada (jika belum ada di environment).
    Format file: KEY=VALUE (satu per baris, bisa ada # untuk comment)
    """
    # Path ke file .env (parent directory dari script ini)
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return

    # Baca setiap baris dari file .env
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        # Skip baris kosong atau comment
        if not line or line.startswith("#") or "=" not in line:
            continue
        
        # Parse KEY=VALUE
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        
        # Set ke environment (hanya jika belum ada)
        os.environ.setdefault(key, value)


def env_int(name: str, default: int) -> int:
    """Ambil nilai integer dari environment variable dengan fallback default.
    
    Args:
        name: Nama environment variable
        default: Nilai default jika tidak ada atau invalid
    
    Returns:
        Nilai integer dari environment atau default jika invalid
    """
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


load_env_file()

BASE_URL = os.getenv("BASE_URL", "http://localhost:5132")
USERNAME = os.getenv("USERNAME", "ammar")
PASSWORD = os.getenv("PASSWORD", "123456")
TOTAL_TRANSAKSI = env_int("TOTAL_TRANSAKSI", 5)
MAX_RETRY_PER_ITEM = env_int("MAX_RETRY_PER_ITEM", 2)

fake = Faker("id_ID")


# ============================================================================
# FUNGSI HELPER UNTUK INTERAKSI DROPDOWN
# ============================================================================

def pick_first_real_option(select_el: Select) -> None:
    """Memilih opsi pertama yang valid di dropdown (mengabaikan opsi kosong/dummy)."""
    for idx, opt in enumerate(select_el.options):
        value = (opt.get_attribute("value") or "").strip()
        text = (opt.text or "").strip()
        if value and "tidak ada" not in text.lower():
            select_el.select_by_index(idx)
            return
    raise RuntimeError("Tidak ada opsi valid di dropdown.")



def wait_select_has_valid_option(driver, wait: WebDriverWait, select_id: str) -> Select:
    """Tunggu sampai dropdown memiliki minimal satu opsi yang valid (bukan kosong/dummy)."""
    def _ready(_):
        el = driver.find_element(By.ID, select_id)
        sel = Select(el)
        valid = 0
        for opt in sel.options:
            value = (opt.get_attribute("value") or "").strip()
            text = (opt.text or "").strip().lower()
            if value and "tidak ada" not in text:
                valid += 1
        return sel if valid > 0 else False

    return wait.until(_ready)



def wait_submit_result(driver, timeout_sec: int = 15) -> tuple[bool, str]:
    """Tunggu hasil submit form dan deteksi apakah sukses atau gagal.
    
    Pengecekan:
    - Sukses: dialog form tertutup (elemen input amount hilang)
    - Gagal: pesan error ditampilkan di layar
    
    Args:
        driver: Selenium WebDriver instance
        timeout_sec: Timeout dalam detik (default: 15 detik)
    
    Returns:
        Tuple (success: bool, message: str)
    """
    end_time = time.time() + timeout_sec
    while time.time() < end_time:
        # Cek sukses: dialog tertutup (input amount hilang)
        if len(driver.find_elements(By.ID, "tx-amount")) == 0:
            return True, "OK"

        # Cek gagal: ada pesan error tampil di layar
        err_nodes = driver.find_elements(
            By.XPATH,
            "//p[@role='alert' or contains(@class,'text-destructive')]",
        )
        for node in err_nodes:
            text = (node.text or "").strip()
            if text:
                return False, text

        # Tunggu sebentar sebelum cek ulang
        time.sleep(0.25)

    # Timeout jika tidak ada tanda sukses atau gagal
    return False, "Timeout: dialog tidak tertutup dan pesan error tidak terbaca."



def close_blocking_dialog_if_any(driver) -> None:
    """Tutup dialog popup yang mungkin menghalangi akses ke tombol "Tambah catatan".
    
    Dialog yang mungkin muncul: info, quota, success, atau pesan penting lainnya.
    Fungsi ini mencari dan mengklik tombol close yang sesuai.
    """
    # Daftar tombol close yang mungkin ada pada berbagai jenis popup
    candidates = [
        "//button[contains(., 'Tutup')]",
        "//button[contains(., 'Mengerti')]",
        "//button[contains(., 'Nanti')]",
    ]
    for xpath in candidates:
        btns = driver.find_elements(By.XPATH, xpath)
        for btn in btns:
            if btn.is_displayed() and btn.is_enabled():
                try:
                    btn.click()
                    time.sleep(0.2)
                    return
                except Exception:  # noqa: BLE001
                    pass



def login(driver, wait: WebDriverWait) -> None:
    """Fungsi login ke aplikasi dengan credentials yang sudah dikonfigurasi.
    
    Flow:
    1. Buka halaman login
    2. Masukkan username
    3. Masukkan password
    4. Klik tombol submit
    5. Tunggu redirect ke halaman dashboard
    """
    # Buka halaman login
    driver.get(f"{BASE_URL}/login")
    
    # Isi username dan tunggu field siap diklik
    wait.until(EC.element_to_be_clickable((By.ID, "identifier"))).send_keys(USERNAME)
    
    # Isi password
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    
    # Klik tombol submit untuk login
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    
    # Tunggu sampai berhasil login (URL berisi '/dashboard')
    wait.until(EC.url_contains("/dashboard"))



def open_form_tambah(wait: WebDriverWait) -> None:
    """Buka form tambah transaksi baru.
    
    Flow:
    1. Cari tombol "Tambah catatan" atau "Tambah"
    2. Tunggu tombol siap diklik
    3. Klik tombol
    4. Tunggu form muncul (input amount visible)
    """
    # Klik tombol "Tambah catatan" atau "Tambah" untuk membuka form
    wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button[contains(., 'Tambah catatan') or contains(., 'Tambah')]",
            )
        )
    ).click()
    
    # Tunggu form muncul dengan mendeteksi input amount
    wait.until(EC.visibility_of_element_located((By.ID, "tx-amount")))



def isi_dan_submit_form(driver, wait: WebDriverWait, nomor: int) -> tuple[int, str]:
    """Isi form transaksi dengan data random dan submit.
    
    Flow:
    1. Generate data random (amount, catatan)
    2. Isi input amount
    3. Tunggu dan pilih opsi currency
    4. Tunggu dan pilih opsi wallet
    5. Tunggu dan pilih opsi category
    6. Isi deskripsi/catatan
    7. Klik tombol Simpan
    8. Tunggu hasil submit (sukses/gagal)
    
    Args:
        driver: Selenium WebDriver instance
        wait: WebDriverWait instance
        nomor: Nomor urut transaksi (untuk keperluan logging)
    
    Returns:
        Tuple (amount_val: int, catatan: str) - nilai yang diinput
    
    Raises:
        RuntimeError: Jika submit gagal
    """
    # Generate data random untuk transaksi
    amount_val = random.randint(10_000, 500_000)
    catatan = f"Auto Selenium #{nomor}: {fake.sentence(nb_words=4)}"

    # Isi input amount
    amount_input = wait.until(EC.element_to_be_clickable((By.ID, "tx-amount")))
    amount_input.clear()
    amount_input.send_keys(str(amount_val))

    # Tunggu dropdown terisi dari data API, kemudian pilih opsi pertama yang valid
    currency_select = wait_select_has_valid_option(driver, wait, "tx-currency")
    pick_first_real_option(currency_select)
    
    wallet_select = wait_select_has_valid_option(driver, wait, "tx-wallet")
    pick_first_real_option(wallet_select)
    
    category_select = wait_select_has_valid_option(driver, wait, "tx-cat")
    pick_first_real_option(category_select)

    # Isi deskripsi/catatan transaksi
    desc = driver.find_element(By.ID, "tx-desc")
    desc.clear()
    desc.send_keys(catatan)

    # Klik tombol Simpan untuk submit form
    submit_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@type='submit' and contains(., 'Simpan')]")
        )
    )
    submit_btn.click()

    # Tunggu hasil submit dan cek apakah sukses atau gagal
    ok, msg = wait_submit_result(driver)
    if not ok:
        raise RuntimeError(f"Submit gagal: {msg}")
    
    return amount_val, catatan



def main() -> None:
    """Fungsi utama automation QA - membuat transaksi secara otomatis.
    
    Flow:
    1. Parse jumlah transaksi dari argument (atau gunakan default dari .env)
    2. Inisialisasi Selenium WebDriver
    3. Login ke aplikasi
    4. Buka halaman transactions
    5. Loop untuk membuat N transaksi:
       - Tutup dialog blocking jika ada
       - Buka form tambah transaksi
       - Isi dan submit form
       - Jika gagal, retry sampai MAX_RETRY_PER_ITEM kali
    6. Tampilkan hasil (jumlah sukses)
    7. Cleanup: tutup browser
    """
    # Baca jumlah transaksi dari argument atau gunakan default
    total = TOTAL_TRANSAKSI
    if len(sys.argv) > 1:
        try:
            total = int(sys.argv[1])
        except ValueError:
            print("Argumen jumlah transaksi tidak valid. Gunakan angka, contoh: python main.py 60")
            return

    # Inisialisasi Selenium WebDriver
    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 25)
    driver.maximize_window()

    sukses = 0
    try:
        # LOGIN KE APLIKASI
        login(driver, wait)
        driver.get(f"{BASE_URL}/transactions")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))

        # LOOP MEMBUAT TRANSAKSI
        for i in range(1, total + 1):
            last_error = None
            
            # Retry loop: coba sampai MAX_RETRY_PER_ITEM kali
            for attempt in range(1, MAX_RETRY_PER_ITEM + 1):
                try:
                    # Tutup popup blocking jika ada
                    close_blocking_dialog_if_any(driver)
                    
                    # Buka form tambah transaksi
                    open_form_tambah(wait)
                    
                    # Isi dan submit form
                    amount, note = isi_dan_submit_form(driver, wait, i)
                    
                    # Sukses: increment counter dan break dari retry loop
                    sukses += 1
                    print(f"✅ [{i}/{total}] Berhasil: Rp{amount} | {note}")
                    time.sleep(0.25)
                    last_error = None
                    break
                    
                except TimeoutException as exc:
                    # Timeout: simpan error dan log
                    last_error = f"Timeout ({exc.__class__.__name__})"
                    print(f"⚠️ [{i}/{total}] Attempt {attempt}: {last_error}")
                    # Reload halaman untuk reset state
                    driver.get(f"{BASE_URL}/transactions")
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                    
                except Exception as exc:  # noqa: BLE001
                    # Error lainnya: simpan error dan log
                    last_error = str(exc)
                    print(f"⚠️ [{i}/{total}] Attempt {attempt}: {last_error}")
                    # Reload halaman untuk reset state
                    driver.get(f"{BASE_URL}/transactions")
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))

            # Jika masih ada error setelah semua retry: hentikan automation
            if last_error is not None:
                print(f"❌ [{i}/{total}] Gagal setelah retry: {last_error}")
                break

        # Tampilkan hasil akhir
        print(f"\nSelesai. Total sukses: {sukses}/{total}")
        time.sleep(2)
    finally:
        # Cleanup: selalu tutup browser
        driver.quit()


if __name__ == "__main__":
    main()