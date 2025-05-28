# pdf_utils.py
import fitz

def search_terms_in_pdf(pdf_path, terms_df):
    findings = []
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        page_text = page.get_text()
        for _, row in terms_df.iterrows():
            term = row['Termo']
            sector = row['Setor']
            if term.lower() in page_text.lower():
                findings.append((sector, term, page_num + 1))
    return findings

def highlight_terms_in_pdf(pdf_path, findings):
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        for sector, term, page_idx in findings:
            if page_idx - 1 == page_num:
                rects = page.search_for(term)
                for r in rects:
                    page.add_highlight_annot(r)
    output_pdf_path = pdf_path.replace(".pdf", "_highlighted.pdf")
    doc.save(output_pdf_path)