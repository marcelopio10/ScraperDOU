import logging
from drive_uploader import list_files_in_drive

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('list_files_test.log'),
        logging.StreamHandler()
    ]
)

def main():
    logging.info("Listando arquivos disponíveis para a conta de serviço")
    items = list_files_in_drive()
    if not items:
        logging.info("Nenhum arquivo encontrado.")
    for item in items:
        logging.info(f"{item['name']} ({item['id']})")

if __name__ == "__main__":
    main()
