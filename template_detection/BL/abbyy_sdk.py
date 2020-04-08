import argparse
import base64
import json
import os
import sys
import traceback

# from ABBYY import CloudOCR
from flask import jsonify
from pathlib import Path
from PyPDF2 import PdfFileReader,PdfFileWriter
from shutil import copy2
try:
    from .ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging()

if sys.platform.startswith('win'):
    import comtypes
    import comtypes.client as cc
    import pythoncom

DEBUG = True


class ABBYY(object):
    '''
    ABBYY SDK Python Wrapper

    Attributes:
        output_type (dict): Parameters (code, extension, function) for output
            type is stored in this dict.
        output_type (str): What the exported output format should be.
        code (int): Code for exporting as particular output type.
        ext (str): Extension of the output file.
        func (str): Function name for exporting as particular output type.
    '''
    def __init__(self, debug=False):
        global DEBUG
        DEBUG = debug

        if sys.platform.startswith('win'):
            pythoncom.CoInitialize()

        self.output_type = {
                            'txt': {
                                    'code': 6,
                                    'extension': '.txt',
                                    'function': 'CreateTextExportParams'
                                    },
                            'xml': {
                                    'code': 7,
                                    'extension': '.xml',
                                    'function': 'CreateXMLExportParams'
                                    }
                            }

        self.export_format = 'xml'
        self.code = None
        self.ext = None
        self.func = None

    def setVars(self, export_format):
        '''
        Set code, extension and function name for exporting based on the output
        type.
        '''
        val = self.output_type[export_format]

        self.export_format = export_format
        self.code = val['code']
        self.ext = val['extension']
        self.func = val['function']

    def getDllFolder(self):
        '''
        Return full path to DLL Folder
        '''
        if(self.is64BitConfiguration()):
            return 'C:\\Program Files\\ABBYY SDK\\12\\FineReader Engine\\Bin64'
        else:
            return 'C:\\Program Files\\ABBYY SDK\\12\\FineReader Engine\\Bin'

    def getSamplesFolder(self):
        '''
        Return full path to Samples directory
        '''
        return 'C:\\ProgramData\\ABBYY\\SDK\\12\\FineReader Engine\\Samples'

    def getCustomerProjectId(self):
        '''
        Return full path to Samples directory
        '''
        return '83FyunWvCj4nuegsxyjY'

    def getLicensePath(self):
        '''
        Return full path to Samples directory
        '''
        return ''

    def getLicensePassword(self):
        '''
        Return full path to Samples directory
        '''
        return ''

    def is64BitConfiguration(self):
        '''
        Determines whether the current configuration is a 64-bit configuration
        '''
        return sys.maxsize > 2**32

    def run(self, input_path, Engine=None):
        log('Runing OCR SDK...')

        if Engine is None:
            # Load ABBYY FineReader Engine
            Engine, EngineLoader = self.loadEngine()

        try:
            # Process with ABBYY FineReader Engine
            ocr_output =  self.processWithEngine(input_path, Engine)
        finally:
            # Unload ABBYY FineReader Engine
            self.unloadEngine(Engine, EngineLoader)

        return {'xml_string': ocr_output}

    def loadEngine(self):
        log('Loading Engine...')
        EngineLoader = cc.CreateObject('FREngine.OutprocLoader')

        # Engine = EngineLoader.GetEngineObject(GetDeveloperSN())
        Engine = EngineLoader.InitializeEngine(
            self.getCustomerProjectId(),
            self.getLicensePath(),
            self.getLicensePassword(),
            '',
            '',
            False)

        return Engine, EngineLoader

    def processWithEngine(self, input_path, Engine):
        try:
            # Setup FREngine
            self.setupFREngine(Engine)

            file_name = Path(input_path).stem
            file_directory = Path(input_path).parent
            result_path = str(file_directory / (str(file_name) + self.ext))

            # Process sample image
            ocr_output = self.processImage(input_path, result_path, Engine)
            return ocr_output
        except:
            logging.exception('error in process with engine!')

    def setupFREngine(self, Engine):
        '''
        Possible profile names are:
        'DocumentConversion_Accuracy', 'DocumentConversion_Speed',
        'DocumentArchiving_Accuracy', 'DocumentArchiving_Speed',
        'BookArchiving_Accuracy', 'BookArchiving_Speed',
        'TextExtraction_Accuracy', 'TextExtraction_Speed',
        'FieldLevelRecognition',
        'BarcodeRecognition_Accuracy', 'BarcodeRecognition_Speed',
        'HighCompressedImageOnlyPdf',
        'BusinessCardsProcessing',
        'EngineeringDrawingsProcessing',
        'Version9Compatibility',
        'Default'
        '''

        Engine.LoadPredefinedProfile('TextExtraction_Accuracy')

    def processImage(self, input_path, result_path, Engine):
        imagePath = input_path
        ocr_data = {}
        logging.debug(f'Input:{imagePath}')

        # Don't recognize PDF file with a textual content, just copy it
        if(Engine.IsPdfWithTextualContent(imagePath, None)):
            copy2(imagePath, result_path)

        # Create document
        document = Engine.CreateFRDocument()

        try:
            # Add image file to document
            document.AddImageFile(imagePath, None, None)

            pagesCount = document.Pages.Count
            for i in range(pagesCount):
                frPage = document.Pages.Element[i]
                imageDoc = frPage.ImageDocument

                # Image related preprocessing functions (See page 364 for functions)
                # imageDoc.RemoveGarbage(None, -1) # See page 386
                # imageDoc.RemoveNoise(0, False) # See page 388

            # Create DocumentProcessingParams object and set parameters (See page 879)
            dpp = Engine.CreateDocumentProcessingParams()
            ppp = dpp.PageProcessingParams

            # PageProcessingParams (See page 893 for parameters)
            # ppp.DetectPictures = True

            # PagePreprocessingParams (See page 885 for parameters)
            ppp.PagePreprocessingParams.CorrectShadowsAndHighlights = 0

            # ObjectsExtractionParams (See page 907 for parameters)
            ppp.ObjectsExtractionParams.EnableAggressiveTextExtraction = True

            # RecognizerParams (See page 911 for parameters)
            # ppp.RecognizerParams.TextTypes = 128 # MICR text type
            ppp.RecognizerParams.DetectTextTypesIndependently = True # Autodetect text type for every block

            # Process document
            document.Process(dpp)
            ocr_output = self.export(result_path, document, Engine)

        except:
            logging.exception('error in Process Image')
        finally:
            document.Close()

        return ocr_output

    def export(self, result_path, document, engine):
        '''
        Export the OCR data into specified output type.

        Args:
            result_path (str): Path of the file where it should be exported to.
            document (FRDocument): The document that needs to be exported.
            engine (FREngine): FineReader Engine

        Returns:
            str: OCR data in string format
        '''
        log('Saving results...')

        export_param_funct = getattr(engine, self.func)
        exportParams = export_param_funct()
        exportParams = self.setExportParams(exportParams)

        # Export (see page 179)
        document.Export(result_path, self.code, exportParams)
        log('Exported to:', result_path)

        # Read the file and remove the file
        with open(result_path, encoding='utf-8-sig') as f:
            string = f.read()
        os.remove(result_path)

        return string

    def setExportParams(self, exportParams):
        if self.export_format == 'xml':
            # Parameters in page 971
            exportParams.WriteCharAttributes = 1 # See page 1250
            exportParams.WriteParagraphStyles = True
        elif self.export_format == 'txt':
            # Parameters in page 962
            exportParams.LayoutRetentionMode = 2
            exportParams.InsertEmptyLineBetweenParagraphs = True

        return exportParams

    def unloadEngine(self, Engine, EngineLoader):
        log('Unloading Engine...')
        EngineLoader.ExplicitlyUnload()
        EngineLoader = None

    def ocr(self, input_path, output_type='xml'):
        if os.name != 'nt':
            logging.debug('SDK only supports Windows')
            return

        try:
            self.setVars(output_type)
            return self.run(input_path)
        except:
            logging.exception('An error occured when trying to OCR')

    def ocr_and_classify(self, input_path, model_path='./models', output_type='xml'):
        if os.name != 'nt':
            message = 'SDK only supports Windows'
            logging.debug(message)
            return {'flag': False, 'message': message}

        self.setVars(output_type) # Set output variable
        result = {}

        Engine, EngineLoader = self.loadEngine() # Load engine

        # Load classification engine and create model
        classification_engine = Engine.CreateClassificationEngine()
        model = classification_engine.CreateModelFromFile(model_path)
        logging.debug(f'Model loaded from{model_path}')

        # Detect template
        fr_doc = Engine.CreateFRDocumentFromImage(input_path, None)
        cl_obj = classification_engine.CreateObjectFromDocument(fr_doc)
        cl_obj.Description = input_path

        results = model.Classify(cl_obj) # Classify the image using the model

        if results:
            classification = {
                'label': results[0].CategoryLabel,
                'probability': results[0].Probability
            }
        else:
            classification = None
            logging.debug('Classification result is empty in ABBYY template detection')

        try:
            # OCR the file too
            xml_string = self.processWithEngine(input_path, Engine)
        except:
            logging.exception('Error occured while OCR-ing image.')
        finally:
            # Unload ABBYY FineReader Engine
            self.unloadEngine(Engine, EngineLoader)

        return {'classification': classification, 'xml_string': xml_string}


    def DisplayMessage(self, message ):
        logging.debug(message)

    def rotation_and_ocr(self, input_path, model_path='./models', output_type='xml'):
        if os.name != 'nt':
            message = 'SDK only supports Windows'
            logging.debug(message)
            return {'flag': False, 'message': message}

        self.setVars(output_type) # Set output variable
        result = {}

        Engine, EngineLoader = self.loadEngine() # Load engine


        '''rotation using abbyy'''
        image_path = input_path
        image_path_folder = os.path.dirname(image_path)
        image_file_name = os.path.basename(image_path)
        try:
            # Page Orientation...
            dpp = Engine.CreateDocumentProcessingParams()

            ppp = dpp.PageProcessingParams                                       # main object..
            ppp.PagePreprocessingParams.CorrectOrientation = True                    # sub-object..
            ppp.PagePreprocessingParams.CorrectInvertedImage = True                # checks if the image is inverted, if so correct.

            #Correct skew in Page Processing stage itself....
            # ppp.PagePreprocessingParams.CorrectSkew = 1
            # ppp.PagePreprocessingParams.CorrectSkewMode = int(0x00000010)

            # Create PrepareImageMode object
            pim = Engine.CreatePrepareImageMode()
            pim.CorrectSkew = True
            pim.CorrectSkewMode = int(0x00000010)

            document = Engine.CreateFRDocument()

            self.DisplayMessage( "Loading image..." )
            # document.AddImageFile( image_path_folder + '\\' + pdf_path, pim, None )
            document.AddImageFile( image_path, pim, None )

            ## Page Process document
            self.DisplayMessage(" Page Processing...")
            document.Process(dpp)

            ## Save results
            self.DisplayMessage( "Saving results..." )
            # FEF_RTF = 0
            FEF_PDF = 4
            PES_Balanced = 1


            pdfParams = Engine.CreatePDFExportParams()
            pdfParams.Scenario = PES_Balanced

            #  Save results to result path with default parameters as pdf file
            exportPath = image_path_folder + '/' + 'o_' + image_file_name
            document.Export(exportPath, FEF_PDF, pdfParams)   # for pdf...

            with open(exportPath, 'rb') as excel:
                blob_data = base64.b64encode(excel.read()).decode('utf-8')

        except Exception as e:
            logging.exception(f'{e}')
        finally:
            ## Close document
            document.Close()

        '''ocr the file too'''
        try:
            xml_string = self.processWithEngine(exportPath, Engine)
        except:
            logging.exception('Error occured while OCR-ing image.')
        finally:
            # Unload ABBYY FineReader Engine
            self.unloadEngine(Engine, EngineLoader)

        return {'blob': blob_data, 'xml_string': xml_string}


log = lambda *args: print(args) if DEBUG else print(end='')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--classify', type=str,
        help='Classify with the model path', default=None)
    parser.add_argument(
        '-i', '--input', type=str,
        help='Input path of the file')
    args = parser.parse_args()

    model_path = args.classify
    input_path = args.input

    abbyy = ABBYY()

    if model_path is not None and abbyy_classification_enabled != 0:
        result = abbyy.ocr_and_classify(input_path, model_path)
    else:
        result = abbyy.rotation_and_ocr(input_path)

    logging.debug(f'{json.dumps(result)}')
