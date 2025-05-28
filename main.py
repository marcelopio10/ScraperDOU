# main.py
import logging
import os
import pandas as pd
from scraper import DOUScraper
from drive_uploader import upload_to_drive, download_file_from_drive, list_files_in_drive
from cleanup_utils import cleanup_local_files
import requests
from io import BytesIO
from time import sleep
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dou_scraper.log'),
        logging.StreamHandler()
    ]
)

def main():
    logging.info("Iniciando o processo de scraping e upload")

    items = list_files_in_drive()
    for item in items:
        logging.info(f"{item['name']} ({item['id']})")

    logging.info("Lendo a planilha de termos do Google Drive")
    file_id = os.getenv("TERMS_FILE_ID")
    local_excel_path = "termos_downloaded.xlsx"
    download_file_from_drive(file_id, local_excel_path)

    logging.info("Lendo a planilha de termos")
    terms_df = pd.read_excel(local_excel_path, engine="openpyxl")

    download_dir = os.getcwd()
    scraper = DOUScraper(download_dir)

    try:
        logging.info("Iniciando navegação e download do PDF")
        scraper.navigate_and_download(terms_df)

        highlighted_pdf_path = scraper.pdf_path.replace(".pdf", "_highlighted.pdf")
        logging.info(f"Upload do PDF destacado: {highlighted_pdf_path}")
        link = upload_to_drive(highlighted_pdf_path)
        logging.info(f"PDF com destaque enviado para o Google Drive: {link}")

        report_path = os.path.join(download_dir, "search_report.xlsx")
        if os.path.exists(report_path):
            logging.info(f"Upload do relatório: {report_path}")
            report_link = upload_to_drive(report_path)
            logging.info(f"Relatório enviado para o Google Drive: {report_link}")
        else:
            logging.warning(f"Arquivo de relatório não encontrado: {report_path}")

    except Exception as e:
        logging.error(f"Erro: {str(e)}")
    finally:
        logging.info("Executando limpeza final")
        scraper.cleanup()

        logging.info("Limpeza dos arquivos locais após upload")
        cleanup_local_files(extensions=[".pdf"], directory=download_dir)

        logging.info("Processo finalizado")

if __name__ == "__main__":
    main()