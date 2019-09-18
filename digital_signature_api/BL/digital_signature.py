from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdftypes import resolve1

from db_utils import DB
from py_zipkin.zipkin import zipkin_span,ZipkinAttrs, create_http_headers_for_new_span

@zipkin_span(service_name='digital_signature', span_name='load_form')
def load_form(filename):
    """Load pdf form contents into a nested list of name/value tuples"""
    with open(filename, 'rb') as file:
        parser = PDFParser(file)
        doc = PDFDocument(parser)
        parser.set_document(doc)

        return [load_fields(resolve1(f)) for f in
            resolve1(doc.catalog['AcroForm'])['Fields']]

@zipkin_span(service_name='digital_signature', span_name='load_fields')
def load_fields(field):
    """Recursively load form fields"""
    form = field.get('Kids', None)
    if form:
        return [load_fields(resolve1(f)) for f in form]
    else:
        # Some field types, like signatures, need extra resolving
        ft = field.get('FT')
        return (str(ft) == "/'Sig'")
   
@zipkin_span(service_name='digital_signature', span_name='flatten')
def flatten(items, seqtypes=(list, tuple)):
    for i, x in enumerate(items):
        while i < len(items) and isinstance(items[i], seqtypes):
            items[i:i+1] = items[i]
    return items

@zipkin_span(service_name='digital_signature', span_name='digitally_signed')
def digitally_signed(filepath: str) -> bool:
    """Checks whether the pdf is digitally signed or not
    Author:
        Akhil
    
    Args:
        filepath The absolutepath of the pdf.
        
    Returns:
        True if the pdf is digitally signed or False.
        
    Note:
        The solution is limited to pdf's signed by using adobe acrobat.
        More specifically pdfminer should have the key AcroForm (eg doc.catalog['AcroForm']) .
        The solution will not work for scanned pdfs.
    """
    try:
        all_sig_bools = load_form(filepath)
        flatten_bools = list(set(flatten(all_sig_bools)))
        if flatten_bools:
            return flatten_bools[0]
        else:
            return False
        
    except FileNotFoundError:
        print ("The file does not exist")
        return False
    except:
        print ("The invoice does not have the key AcroForm...is it scanned? or ?")
        return False

@zipkin_span(service_name='digital_signature', span_name='is_pdf_signed')
def is_pdf_signed(case_id, file_name):
    db_config = {
        'host': 'extraction_db',
        'port': 3306,
        'user': 'root',
        'password': 'root'
    }
    db = DB('extraction', **db_config)
    # db = DB('extraction')
    
    file_path ='./files/' + file_name
    digital_signature = 0

    if digitally_signed(file_path):
        digital_signature = 1

    try:
        query = 'INSERT INTO `validation` (`case_id`, `Digital Signature`) VALUES (%s, %s)'
        params = [case_id, digital_signature]
        db.execute(query, params=params)
        return {'flag': True}
    except:
        traceback.print_exc()
        print(f'Error occured while updating value of `Digital Signature` in validation. Check logs.')
        return {'flag': False}