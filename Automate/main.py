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


def load_env_file() -> None:
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def env_int(name: str, default: int) -> int:
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


def pick_first_real_option(select_el: Select) -> None:
    for idx, opt in enumerate(select_el.options):
        value = (opt.get_attribute("value") or "").strip()
        text = (opt.text or "").strip()
        if value and "tidak ada" not in text.lower():
            select_el.select_by_index(idx)
            return
    raise RuntimeError("Tidak ada opsi valid di dropdown.")


def wait_select_has_valid_option(driver, wait: WebDriverWait, select_id: str) -> Select:
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
    end_time = time.time() + timeout_sec
    while time.time() < end_time:
        # sukses: dialog tertutup (input amount hilang)
        if len(driver.find_elements(By.ID, "tx-amount")) == 0:
            return True, "OK"

        # gagal: ada pesan error tampil
        err_nodes = driver.find_elements(
            By.XPATH,
            "//p[@role='alert' or contains(@class,'text-destructive')]",
        )
        for node in err_nodes:
            text = (node.text or "").strip()
            if text:
                return False, text

        time.sleep(0.25)

    return False, "Timeout: dialog tidak tertutup dan pesan error tidak terbaca."


def close_blocking_dialog_if_any(driver) -> None:
    # Beberapa popup app (info/quota/success) bisa nutup tombol "Tambah catatan".
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
    driver.get(f"{BASE_URL}/login")
    wait.until(EC.element_to_be_clickable((By.ID, "identifier"))).send_keys(USERNAME)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard"))


def open_form_tambah(wait: WebDriverWait) -> None:
    wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button[contains(., 'Tambah catatan') or contains(., 'Tambah')]",
            )
        )
    ).click()
    wait.until(EC.visibility_of_element_located((By.ID, "tx-amount")))


def isi_dan_submit_form(driver, wait: WebDriverWait, nomor: int) -> tuple[int, str]:
    amount_val = random.randint(10_000, 500_000)
    catatan = f"Auto Selenium #{nomor}: {fake.sentence(nb_words=4)}"

    amount_input = wait.until(EC.element_to_be_clickable((By.ID, "tx-amount")))
    amount_input.clear()
    amount_input.send_keys(str(amount_val))

    # Pastikan dropdown sudah terisi dari data API sebelum dipilih.
    currency_select = wait_select_has_valid_option(driver, wait, "tx-currency")
    pick_first_real_option(currency_select)
    wallet_select = wait_select_has_valid_option(driver, wait, "tx-wallet")
    pick_first_real_option(wallet_select)
    category_select = wait_select_has_valid_option(driver, wait, "tx-cat")
    pick_first_real_option(category_select)

    desc = driver.find_element(By.ID, "tx-desc")
    desc.clear()
    desc.send_keys(catatan)

    submit_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@type='submit' and contains(., 'Simpan')]")
        )
    )
    submit_btn.click()

    ok, msg = wait_submit_result(driver)
    if not ok:
        raise RuntimeError(f"Submit gagal: {msg}")
    return amount_val, catatan


def main() -> None:
    total = TOTAL_TRANSAKSI
    if len(sys.argv) > 1:
        try:
            total = int(sys.argv[1])
        except ValueError:
            print("Argumen jumlah transaksi tidak valid. Gunakan angka, contoh: python main.py 60")
            return

    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 25)
    driver.maximize_window()

    sukses = 0
    try:
        login(driver, wait)
        driver.get(f"{BASE_URL}/transactions")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))

        for i in range(1, total + 1):
            last_error = None
            for attempt in range(1, MAX_RETRY_PER_ITEM + 1):
                try:
                    close_blocking_dialog_if_any(driver)
                    open_form_tambah(wait)
                    amount, note = isi_dan_submit_form(driver, wait, i)
                    sukses += 1
                    print(f"✅ [{i}/{total}] Berhasil: Rp{amount} | {note}")
                    time.sleep(0.25)
                    last_error = None
                    break
                except TimeoutException as exc:
                    last_error = f"Timeout ({exc.__class__.__name__})"
                    print(f"⚠️ [{i}/{total}] Attempt {attempt}: {last_error}")
                    driver.get(f"{BASE_URL}/transactions")
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                except Exception as exc:  # noqa: BLE001
                    last_error = str(exc)
                    print(f"⚠️ [{i}/{total}] Attempt {attempt}: {last_error}")
                    driver.get(f"{BASE_URL}/transactions")
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))

            if last_error is not None:
                print(f"❌ [{i}/{total}] Gagal setelah retry: {last_error}")
                break

        print(f"\nSelesai. Total sukses: {sukses}/{total}")
        time.sleep(2)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()