### entrypoint.sh
#!/bin/bash

# Executa o script principal diariamente (simulação com loop para Render)
while true; do
  echo "Executando scraper..."
  python main.py
  echo "Aguardando 24h para nova execução..."
  sleep 86400
done