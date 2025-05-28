# report_utils.py
import os
import pandas as pd
from datetime import datetime

def generate_report(download_dir, findings):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_df = pd.DataFrame(findings, columns=["Setor", "Termo", "Página"])
    report_df['Timestamp'] = timestamp
    report_path = os.path.join(download_dir, "search_report.xlsx")
    if os.path.exists(report_path):
        existing_df = pd.read_excel(report_path)
        updated_df = pd.concat([existing_df, report_df], ignore_index=True)
        updated_df.to_excel(report_path, index=False)
    else:
        report_df.to_excel(report_path, index=False)