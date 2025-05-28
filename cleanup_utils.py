import glob
import logging
import os

def cleanup_local_files(extensions, directory):
    for ext in extensions:
        pattern = os.path.join(directory, f"*{ext}")
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                logging.info(f"Arquivo removido: {file_path}")
            except Exception as e:
                logging.warning(f"Erro ao remover {file_path}: {str(e)}")
