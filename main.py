import os
import io
import logging
import time
from datetime import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import PyPDF2 # Ou sua biblioteca de manipulação de PDF, por exemplo, PyPDF2
import requests
import base64

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account

# --- Configuração de Logging ---
# Configura o logging para exibir mensagens INFO e DEBUG no console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# Opcional: Se quiser ver logs mais detalhados de bibliotecas:
# logging.getLogger('selenium').setLevel(logging.DEBUG)
# logging.getLogger('urllib3').setLevel(logging.DEBUG)
# logging.getLogger('googleapiclient').setLevel(logging.DEBUG)
# logging.getLogger('google_auth_httplib2').setLevel(logging.DEBUG)

# --- Variáveis de Ambiente e Configurações ---
# Caminho para o arquivo de credenciais da conta de serviço Google
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE", "servicescraperdou.json")
# ID da pasta no Google Drive (se você ainda estiver usando para outros uploads/downloads)
DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID") or \
                  os.getenv("DRIVE_FOLDER_ID") or \
                  os.getenv("FOLDER_ID")
# ID do arquivo da planilha de termos no Google Drive
TERMS_FILE_ID = os.getenv("TERMS_FILE_ID")

# Variáveis para o GitHub (passadas pelo GitHub Actions)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = os.getenv("REPO_OWNER")
REPO_NAME = os.getenv("REPO_NAME")
BRANCH = os.getenv("BRANCH", "main") # Padrão 'main' para o branch

# Diretório para salvar arquivos temporários (PDFs e relatórios)
OUTPUT_DIR = "output_files"
PDF_DOWNLOAD_DIR = os.path.join(OUTPUT_DIR, "PDF") # Subdiretório para PDFs
if not os.path.exists(PDF_DOWNLOAD_DIR):
    os.makedirs(PDF_DOWNLOAD_DIR)

# --- Classes e Funções de Serviço ---

class GoogleDriveService:
    SCOPES = ["https://www.googleapis.com/auth/drive"]

    def __init__(self):
        logging.info("Iniciando autenticação do serviço Google Drive...")
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=self.SCOPES)
            # Sem delegação de domínio para uma conta @gmail.com padrão
            # Se fosse Google Workspace com DWD, seria:
            # DELEGATE_EMAIL = os.getenv("DELEGATE_EMAIL")
            # if DELEGATE_EMAIL:
            #     self.credentials = self.credentials.with_subject(DELEGATE_EMAIL)

            self.service = build("drive", "v3", credentials=self.credentials)
            logging.info("Autenticação do serviço Google Drive concluída com sucesso.")
        except Exception as e:
            logging.error(f"Erro na autenticação do serviço Google Drive: {e}")
            raise

    def download_file(self, file_id, dest_path):
        """Faz o download de um arquivo do Google Drive."""
        logging.info(f"Iniciando download do arquivo com ID: {file_id} para {dest_path}")
        try:
            # supportsAllDrives=True é importante para Shared Drives
            request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)
            with io.FileIO(dest_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        logging.info(f"Download {int(status.progress() * 100)}%.")
            logging.info(f"Download concluído para: {dest_path}")
            return True
        except Exception as e:
            logging.error(f"Erro ao baixar o arquivo {file_id}: {e}")
            return False

    def list_files_in_folder(self, folder_id):
        """Lista os arquivos em uma pasta específica do Google Drive."""
        logging.info(f"Listando arquivos na pasta: {folder_id}")
        try:
            query = f"'{folder_id}' in parents"
            results = self.service.files().list(
                q=query,
                pageSize=20,
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            files = results.get("files", [])
            return files
        except Exception as e:
            logging.error(f"Erro ao listar arquivos na pasta {folder_id}: {e}")
            return []

    def upload_file(self, file_path, mime_type="application/pdf", folder_id=None):
        """Realiza o upload de um arquivo para o Google Drive."""
        target_folder_id = folder_id if folder_id else DRIVE_FOLDER_ID
        if not target_folder_id:
            logging.error("ID da pasta do Google Drive não definido para upload.")
            return None

        logging.info(f"Iniciando upload do arquivo: {file_path} para pasta {target_folder_id}")
        file_metadata = {
            "name": os.path.basename(file_path),
            "parents": [target_folder_id]
        }
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id",
                supportsAllDrives=True
            ).execute()
            logging.info(f"Upload concluído. File ID: {file.get('id')}")
            return file.get("id")
        except Exception as e:
            logging.error(f"Erro ao fazer upload do arquivo {file_path}: {e}")
            return None

class GitHubUploader:
    def __init__(self):
        self.github_token = GITHUB_TOKEN
        self.repo_owner = REPO_OWNER
        self.repo_name = REPO_NAME
        self.branch = BRANCH

        if not self.github_token or not self.repo_owner or not self.repo_name:
            logging.error("Variáveis GITHUB_TOKEN, REPO_OWNER ou REPO_NAME não configuradas.")
            raise ValueError("Erro de configuração de variáveis do GitHub. Não é possível inicializar o uploader.")

        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = "https://api.github.com"

    def github_api_request(self, endpoint, method="GET", data=None):
        """Faz uma requisição à API REST do GitHub."""
        url = f"{self.base_url}/{endpoint}"
        logging.debug(f"{method} {url}")
        response = requests.request(method, url, headers=self.headers, json=data)
        response.raise_for_status() # Lança um erro para status de erro (4xx, 5xx)
        return response.json()

    def upload_file(self, local_file_path, github_folder_path=""):
        """
        Realiza o upload de um arquivo local para um repositório GitHub.
        Se o arquivo já existe, ele é atualizado.
        """
        file_name = os.path.basename(local_file_path)
        # Constrói o caminho completo no GitHub, incluindo a pasta
        github_content_path = os.path.join(github_folder_path, file_name).replace("\\", "/")
        logging.info(f"Enviando '{local_file_path}' para 'github.com/{self.repo_owner}/{self.repo_name}/{github_content_path}' no branch '{self.branch}'")

        try:
            with open(local_file_path, 'rb') as f:
                content_bytes = f.read()
            encoded_content = base64.b64encode(content_bytes).decode('utf-8')

            sha = None
            # Tenta obter o SHA do arquivo se ele já existe (para atualização)
            try:
                # O endpoint para buscar conteúdo é /repos/:owner/:repo/contents/:path
                get_response = self.github_api_request(
                    f"repos/{self.repo_owner}/{self.repo_name}/contents/{github_content_path}?ref={self.branch}",
                    method="GET"
                )
                sha = get_response.get('sha')
                logging.debug(f"Arquivo '{github_content_path}' encontrado no GitHub. SHA: {sha}")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    logging.debug(f"Arquivo '{github_content_path}' não encontrado no GitHub. Será criado.")
                    sha = None
                else:
                    logging.error(f"Erro inesperado ao verificar arquivo no GitHub: {e.response.json()}")
                    return False
            except Exception as e:
                logging.error(f"Erro ao verificar arquivo no GitHub (erro geral): {e}")
                return False

            # Prepara os dados para a requisição PUT (criar/atualizar)
            commit_message = f"Adiciona {file_name} via ScraperDOU" if not sha else f"Atualiza {file_name} via ScraperDOU"
            data = {
                "message": commit_message,
                "content": encoded_content,
                "branch": self.branch
            }
            if sha:
                data["sha"] = sha # Necessário para atualizar um arquivo existente

            # Realiza o upload (PUT)
            upload_response = self.github_api_request(
                f"repos/{self.repo_owner}/{self.repo_name}/contents/{github_content_path}",
                method="PUT",
                data=data
            )
            logging.info(f"Upload de '{file_name}' para o GitHub concluído. Commit SHA: {upload_response.get('commit', {}).get('sha')}")
            return True

        except requests.exceptions.HTTPError as e:
            logging.error(f"Erro HTTP ao enviar '{file_name}' para o GitHub: {e.response.status_code} - {e.response.json()}")
            return False
        except Exception as e:
            logging.error(f"Erro geral ao enviar '{file_name}' para o GitHub: {e}")
            return False

# --- Funções de Manipulação de Arquivos e Lógica do DOU ---

def cleanup_local_files(directory):
    """Remove todos os arquivos do diretório especificado."""
    logging.info(f"Executando limpeza dos arquivos locais em: {directory}")
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
                logging.info(f"Arquivo removido: {file_path}")
            elif os.path.isdir(file_path):
                # Opcional: para remover subdiretórios vazios
                # os.rmdir(file_path)
                pass
        except Exception as e:
            logging.error(f"Falha ao remover {file_path}. Razão: {e}")

def get_dou_date_str():
    """Retorna a data atual no formato YYYY_MM_DD."""
    return datetime.now().strftime("%Y_%m_%d")

def get_dou_pdf_filename(date_str):
    """Retorna o nome esperado do arquivo PDF do DOU."""
    # O nome real do arquivo baixado pode variar, mas usaremos este para renomear/identificar
    return f"{date_str}_ASSINADO_do1.pdf"

def setup_chrome_options(download_dir):
    """Configura as opções do Chrome para download automático de PDFs."""
    # Garante que o diretório usado pelo Chrome seja absoluto
    abs_download_dir = os.path.abspath(download_dir)

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Roda o navegador em modo headless
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-dev-tools")
    chrome_options.add_argument("--remote-debugging-port=9222")

    # Preferências de download
    prefs = {
        "download.default_directory": abs_download_dir,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
        "download.directory_upgrade": True,
        "safeBrowse.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    return chrome_options

def download_dou_pdf(driver, date_str, download_dir):
    """Navega no site do DOU e baixa o PDF."""
    logging.info("Iniciando navegação e download do PDF")
    dou_url = "https://www.in.gov.br/leiturajornal"
    
    try:
        logging.info(f"Acessando a página do DOU: {dou_url}")
        driver.get(dou_url)
        # Define o tamanho da janela para garantir que elementos estejam visíveis
        driver.set_window_size(1024, 768)
        
        # Espera pelo botão do diário completo
        wait = WebDriverWait(driver, 30)
        btn_diario_completo = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn-diario-completo"))
        )
        
        logging.info("Tentando clicar em .btn-diario-completo")
        # Rola o elemento para a visualização antes de clicar
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_diario_completo)
        btn_diario_completo.click()
        
        # Espera pela nova janela/aba do PDF
        # Obtém todas as janelas/abas abertas
        window_handles = driver.window_handles
        # Troca para a nova janela/aba (geralmente a última)
        driver.switch_to.window(window_handles[-1])
        
        logging.info("Esperando a conclusão do download")
        
        # Espera até que o arquivo PDF apareça no diretório de download
        downloaded_file = None
        start_time = time.time()
        timeout = 300000  # 2 minutos de timeout para o download

        while time.time() - start_time < timeout:
            list_of_files = [f for f in os.listdir(download_dir) if f.endswith(".pdf")]
            logging.info(f"Arquivos PDF encontrados: {list_of_files}")
            if list_of_files:
                # Usa o arquivo PDF mais recente encontrado
                list_of_files.sort(key=lambda f: os.path.getmtime(os.path.join(download_dir, f)), reverse=True)
                downloaded_file = os.path.join(download_dir, list_of_files[0])
                # Espera até que o download esteja completo (tamanho do arquivo não mude)
                current_size = -1
                for _ in range(10): # Checa 10 vezes com 1 segundo de intervalo
                    time.sleep(1)
                    if os.path.exists(downloaded_file):
                        new_size = os.path.getsize(downloaded_file)
                        if new_size == current_size and new_size > 0:
                            logging.info(f"Download finalizado: {downloaded_file}")
                            return downloaded_file
                        current_size = new_size
                    else:
                        logging.warning(f"Arquivo {downloaded_file} ainda não existe após {_+1}s.")
                logging.warning(f"Download de {downloaded_file} parece não ter terminado após o tempo de espera de estabilidade.")
                if os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) > 0:
                     logging.info(f"Download parece estar Ok, tamanho: {os.path.getsize(downloaded_file)} bytes")
                     return downloaded_file
                break # Sai do loop se o arquivo não estiver estável

            time.sleep(2) # Espera antes de verificar novamente
        
        logging.error("Timeout ou falha ao baixar o PDF do DOU.")
        return None

    except Exception as e:
        logging.error(f"Erro durante o processo de download do DOU: {e}")
        return None
    finally:
        # Volta para a janela original antes de fechar o driver se houver múltiplas abas
        if len(driver.window_handles) > 1:
            driver.switch_to.window(window_handles[0])


def analyze_and_highlight_pdf(pdf_path, terms_df, output_dir):
    """
    Simula a análise e destaque do PDF.
    Você precisará implementar a lógica real de leitura e manipulação do PDF aqui.
    Para este exemplo, apenas cria um arquivo de saída simulado.
    """
    logging.info(f"Iniciando análise do PDF: {pdf_path}")
    output_pdf_path = os.path.join(output_dir, os.path.basename(pdf_path).replace(".pdf", "_highlighted.pdf"))
    
    try:
        # AQUI VOCÊ IMPLEMENTARIA A LÓGICA REAL:
        # 1. Carregar o PDF (ex: PyPDF2.PdfReader)
        # 2. Extrair texto
        # 3. Iterar pelos termos em terms_df
        # 4. Destacar termos no PDF (PyPDF2 não faz destaque visual diretamente,
        #    você precisaria de bibliotecas como reportlab ou PyMuPDF/fitz)
        #    Para um destaque visual complexo, PyMuPDF (fitz) é a melhor opção.
        #    Se você está apenas buscando texto, PyPDF2 é suficiente.

        # Exemplo simulado: Apenas copia o arquivo e adiciona um "_highlighted"
        # Isso NÃO faz o destaque real, apenas simula a criação do arquivo de saída.
        with open(pdf_path, 'rb') as infile:
            with open(output_pdf_path, 'wb') as outfile:
                outfile.write(infile.read())
        
        logging.info(f"PDF com destaque simulado criado: {output_pdf_path}")
        return output_pdf_path
    except Exception as e:
        logging.error(f"Erro ao analisar/destacar PDF: {e}")
        return None

def generate_search_report(terms_df, output_dir):
    """
    Simula a geração de um relatório de pesquisa.
    Você precisaria implementar a lógica real para criar este relatório.
    """
    logging.info("Gerando relatório de pesquisa...")
    report_path = os.path.join(output_dir, "search_report.xlsx")
    
    try:
        # Exemplo: Apenas salva o DataFrame de termos como um relatório (simulado)
        terms_df.to_excel(report_path, index=False)
        logging.info(f"Relatório de pesquisa simulado criado: {report_path}")
        return report_path
    except Exception as e:
        logging.error(f"Erro ao gerar relatório de pesquisa: {e}")
        return None

# --- Função Principal ---

def main():
    logging.info("Iniciando o processo de scraping e upload")

    google_drive_service = None
    try:
        google_drive_service = GoogleDriveService()
    except ValueError as e:
        logging.error(f"Erro fatal ao inicializar o serviço Google Drive: {e}")
        exit(1) # Sai se a autenticação do Drive falhar

    github_uploader = None
    try:
        github_uploader = GitHubUploader()
    except ValueError as e:
        logging.error(f"Erro fatal ao inicializar o uploader do GitHub: {e}")
        # Decida se você quer sair aqui ou apenas pular o upload para o GitHub
        exit(1) # Sai se o GitHub uploader não puder ser configurado

    # --- 1. Baixar a planilha de termos do Google Drive ---
    terms_df = pd.DataFrame() # DataFrame vazio por padrão
    if TERMS_FILE_ID:
        logging.info(f"Lendo a planilha de termos do Google Drive (ID: {TERMS_FILE_ID})")
        local_terms_path = os.path.join(OUTPUT_DIR, "termos.xlsx")
        if google_drive_service.download_file(TERMS_FILE_ID, local_terms_path):
            try:
                terms_df = pd.read_excel(local_terms_path)
                logging.info(f"Planilha de termos lida com sucesso. {len(terms_df)} termos encontrados.")
            except Exception as e:
                logging.error(f"Erro ao ler a planilha Excel baixada: {e}")
        else:
            logging.error("Falha ao baixar a planilha de termos do Google Drive. Prosseguindo sem termos.")
    else:
        logging.warning("TERMS_FILE_ID não definido. Não será possível ler a planilha de termos do Google Drive.")
        # Opcional: Crie um DataFrame de termos de exemplo se não houver um arquivo
        terms_df = pd.DataFrame({'Termo': ['exemplo', 'teste']})
        logging.info("Usando termos de exemplo.")


    # --- 2. Configurar Selenium e baixar PDF do DOU ---
    driver = None
    downloaded_pdf_path = None
    try:
        chrome_options = setup_chrome_options(PDF_DOWNLOAD_DIR)
        # O Selenium Manager já deve lidar com o driver no GitHub Actions
        driver = webdriver.Chrome(options=chrome_options)
        
        today_date_str = get_dou_date_str()
        downloaded_pdf_path = download_dou_pdf(driver, today_date_str, PDF_DOWNLOAD_DIR)

        if downloaded_pdf_path:
            logging.info(f"PDF do DOU baixado para: {downloaded_pdf_path}")
        else:
            logging.error("Não foi possível baixar o PDF do DOU. Verifique os logs do Selenium.")

    except Exception as e:
        logging.error(f"Erro fatal durante a operação do Selenium: {e}")
    finally:
        if driver:
            logging.info("Fechando navegador")
            driver.quit()

    # --- 3. Analisar e Destaque PDF (se baixado) ---
    highlighted_pdf_path = None
    if downloaded_pdf_path and not terms_df.empty:
        highlighted_pdf_path = analyze_and_highlight_pdf(downloaded_pdf_path, terms_df, PDF_DOWNLOAD_DIR)
        if highlighted_pdf_path:
            logging.info(f"PDF com destaque salvo localmente em: {highlighted_pdf_path}")
        else:
            logging.error("Falha ao criar PDF com destaque.")

    # --- 4. Gerar Relatório de Pesquisa ---
    report_xlsx_path = generate_search_report(terms_df, OUTPUT_DIR)
    if report_xlsx_path:
        logging.info(f"Relatório de pesquisa salvo localmente em: {report_xlsx_path}")
    else:
        logging.error("Falha ao gerar relatório de pesquisa.")

    # --- 5. Upload para o GitHub ---
    if github_uploader: # Verifica se o uploader foi inicializado com sucesso
        if highlighted_pdf_path:
            logging.info(f"Enviando PDF destacado para o GitHub: {highlighted_pdf_path}")
            if github_uploader.upload_file(highlighted_pdf_path, github_folder_path="PDFs"): # Salva em uma pasta 'PDFs' no GitHub
                logging.info(f"PDF com destaque salvo no GitHub: {highlighted_pdf_path}")
            else:
                logging.error(f"Falha ao enviar PDF com destaque para o GitHub: {highlighted_pdf_path}")
        else:
            logging.warning("Nenhum PDF destacado para enviar para o GitHub.")

        if report_xlsx_path:
            logging.info(f"Enviando relatório para o GitHub: {report_xlsx_path}")
            if github_uploader.upload_file(report_xlsx_path, github_folder_path="Reports"): # Salva em uma pasta 'Reports' no GitHub
                logging.info(f"Relatório salvo no GitHub: {report_xlsx_path}")
            else:
                logging.error(f"Falha ao enviar relatório para o GitHub: {report_xlsx_path}")
        else:
            logging.warning("Nenhum relatório para enviar para o GitHub.")
    else:
        logging.error("Uploader do GitHub não disponível. Pulando uploads para o GitHub.")

    # --- 6. Limpeza Final ---
    logging.info("Executando limpeza final")
    cleanup_local_files(PDF_DOWNLOAD_DIR)
    cleanup_local_files(OUTPUT_DIR) # Limpa a pasta principal de output também, para o relatório e termos.xlsx
    logging.info("Processo finalizado")

if __name__ == "__main__":
    main()
