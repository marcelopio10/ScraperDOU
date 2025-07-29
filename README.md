# Scraper DOU

Este projeto automatiza o download, análise e envio de PDFs do Diário Oficial da União (DOU).
Os resultados (PDF destacado e relatório) agora são versionados diretamente no repositório GitHub configurado.
O Google Drive é utilizado apenas para baixar a planilha de termos, caso um `TERMS_FILE_ID` seja fornecido.

## Requisitos
- Docker instalado
- Conta no [Railway](https://railway.app/)

## Executar localmente com Docker
```bash
docker build -t scraperdou .
docker run --rm -v $PWD:/app scraperdou
```

## Deploy no Railway
1. Crie um novo projeto
2. Faça push do repositório para o GitHub
3. Conecte o GitHub ao Railway
4. Adicione as variáveis de ambiente conforme necessário
5. Configure para rodar `python run_daily.py`

## Variáveis e arquivos secretos
- `servicescraperdou.json` (não subir no GitHub)
- `credentials.json` (não subir no GitHub)
- Variável de ambiente `TERMS_FILE_ID` com o ID da planilha de termos no Google Drive
- (Opcional) `GOOGLE_DRIVE_FOLDER_ID` (ou `DRIVE_FOLDER_ID`/`FOLDER_ID`) caso deseje listar arquivos ou baixar a planilha de termos a partir do Google Drive
- `DELEGATE_EMAIL` com o email a ser impersonado se estiver usando uma conta de serviço com delegação de domínio
- `GITHUB_TOKEN` token pessoal para autenticar no GitHub
- `GITHUB_REPO` no formato `usuario/repositorio` onde os arquivos serão enviados
- `GITHUB_BRANCH` (opcional) branch onde os arquivos serão adicionados, padrão `main`
- `TARGET_REPO` e `TARGET_BRANCH` podem ser usados como sinônimos de `GITHUB_REPO` e `GITHUB_BRANCH`
- `LOG_LEVEL` define o nível de log (padrão `DEBUG`)
- `LOCAL_OUTPUT_DIR` pasta onde os arquivos são salvos caso o envio para o GitHub falhe (padrão `output_files`)

**Importante:** Verifique permissões e IDs de arquivos/pastas usados no Google Drive.
