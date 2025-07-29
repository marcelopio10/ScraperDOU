# main.py
import logging
import os
import pandas as pd
from scraper import DOUScraper
from drive_uploader import download_file_from_drive, list_files_in_drive
from github_utils import upload_file_to_github
from cleanup_utils import cleanup_local_files
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.DEBUG),
    format='%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s',
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
    if not file_id:
        for item in items:
            if item["name"].lower() == "termos.xlsx":
                file_id = item["id"]
                logging.info("TERMS_FILE_ID não definido, usando ID encontrado: %s", file_id)
                break
        if not file_id:
            raise EnvironmentError(
                "TERMS_FILE_ID não definido e arquivo termos.xlsx não encontrado"
            )

    local_excel_path = "termos_downloaded.xlsx"
    download_file_from_drive(file_id, local_excel_path)

    logging.info("Lendo a planilha de termos")
    terms_df = pd.read_excel(local_excel_path, engine="openpyxl")

    download_dir = os.path.join(os.getcwd(), "PDF")
    os.makedirs(download_dir, exist_ok=True)
    scraper = DOUScraper(download_dir)

    try:
        logging.info("Iniciando navegação e download do PDF")
        scraper.navigate_and_download(terms_df)

        highlighted_pdf_path = scraper.pdf_path.replace(".pdf", "_highlighted.pdf")
        logging.info(f"Enviando PDF destacado para o GitHub: {highlighted_pdf_path}")
        github_link = upload_file_to_github(highlighted_pdf_path)
        if github_link:
            logging.info(f"PDF com destaque salvo no GitHub: {github_link}")

        report_path = os.path.join(download_dir, "search_report.xlsx")
        if os.path.exists(report_path):
            logging.info(f"Enviando relatório para o GitHub: {report_path}")
            github_report = upload_file_to_github(report_path)
            if github_report:
                logging.info(f"Relatório salvo no GitHub: {github_report}")
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
