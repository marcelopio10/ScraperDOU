# Scraper DOU

Este projeto automatiza o download, análise e envio de PDFs do Diário Oficial da União (DOU).

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

**Importante:** Verifique permissões e IDs de arquivos/pastas usados no Google Drive.
