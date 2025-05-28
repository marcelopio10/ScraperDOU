import schedule
import time
import logging
from main import main

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

def job():
    logging.info("Executando rotina diária do scraper")
    main()

# Agendar para executar 1x por dia às 06:00 da manhã
schedule.every().day.at("08:00").do(job)

logging.info("Agendador iniciado. Aguardando execução diária...")

while True:
    schedule.run_pending()
    time.sleep(60)