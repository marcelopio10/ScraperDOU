# scraper.py
import os
import time
import glob
import logging
import re
import requests
import fitz
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException
from tempfile import mkdtemp
from pdf_utils import search_terms_in_pdf, highlight_terms_in_pdf
from report_utils import generate_report

class DOUScraper:
    def __init__(self, download_dir):
        self.url = "https://www.in.gov.br/leiturajornal"
        self.findings = []
        self.pdf_path = None
        self.download_dir = download_dir
        self.setup_driver()

    def setup_driver(self):
        chrome_options = Options()
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        user_data_dir = mkdtemp()
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

    def is_download_complete(self):
        for ext in ['.crdownload', '.tmp', '.partial']:
            if glob.glob(os.path.join(self.download_dir, f'*{ext}')):
                return False
        return True

    def wait_for_download(self, timeout=600):
        logging.info("Aguardando conclusão do download do PDF")
        start_time = time.time()
        time.sleep(5)
        while time.time() - start_time < timeout:
            pdf_files = [f for f in os.listdir(self.download_dir) if f.endswith('.pdf')]
            logging.info(f"Arquivos PDF encontrados: {pdf_files}")
            if pdf_files and self.is_download_complete():
                pdf_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.download_dir, x)), reverse=True)
                self.pdf_path = os.path.join(self.download_dir, pdf_files[0])
                size = os.path.getsize(self.pdf_path)
                logging.info(f"Arquivo {self.pdf_path} tem {size} bytes")
                if size > 0:
                    logging.info(f"Download finalizado: {self.pdf_path}")
                    return True
            elapsed = int(time.time() - start_time)
            if elapsed % 30 == 0:
                logging.info(f"Esperando... {elapsed}s se passaram")
            time.sleep(2)
        logging.error("Timeout ao esperar o download do PDF")
        return False

    def retry_click(self, by, selector, max_attempts=3):
        for attempt in range(max_attempts):
            try:
                logging.info(f"Tentando clicar em {selector} (tentativa {attempt+1})")
                element = self.wait.until(EC.element_to_be_clickable((by, selector)))
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(1)
                element.click()
                return True
            except StaleElementReferenceException:
                time.sleep(1)
        return False

    def navigate_and_download(self, terms_df):
        logging.info("Acessando a página do DOU")
        self.driver.get(self.url)
        time.sleep(5)
        self.driver.set_window_size(1024, 768)
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".btn-diario-completo")))

        if not self.retry_click(By.CSS_SELECTOR, ".btn-diario-completo"):
            raise Exception("Falha ao clicar em .btn-diario-completo")

        time.sleep(3)
        original_window = self.driver.current_window_handle

        if not self.retry_click(By.CSS_SELECTOR, "a > img"):
            raise Exception("Falha ao clicar na imagem")

        self.wait.until(lambda d: len(d.window_handles) > 1)
        for window_handle in self.driver.window_handles:
            if window_handle != original_window:
                self.driver.switch_to.window(window_handle)
                break

        logging.info("Esperando a conclusão do download")
        if not self.wait_for_download():
            raise Exception("Download do PDF não completou")

        logging.info("Iniciando análise do PDF")
        self.findings = search_terms_in_pdf(self.pdf_path, terms_df)
        highlight_terms_in_pdf(self.pdf_path, self.findings)
        generate_report(self.download_dir, self.findings)

    def cleanup(self):
        if hasattr(self, 'driver'):
            logging.info("Fechando navegador")
            self.driver.quit()
        for pattern in ['*.crdownload', '*.tmp', '*.partial']:
            files = glob.glob(os.path.join(self.download_dir, pattern))
            for file in files:
                try:
                    os.remove(file)
                except Exception:
                    pass