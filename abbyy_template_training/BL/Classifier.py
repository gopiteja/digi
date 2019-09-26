from EngineHolder import EngineHolder
import os
from ClassifierTypeEnum import ClassifierTypeEnum
from ClassifiedImage import ClassifiedImage
from ace_logger import Logging
logging = Logging().getLogger('ace')


class ClassificationOptions:
    imagesfolder = None
    correctorientation = False


class Classifier:
    classificationoptions = ClassificationOptions()
    recognizerparams = None
    preprocessparams = None
    supportedfiletypes = [".bmp", ".gif", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".pdf"]

    def __init__(self,_imagesfolder):
        self.classificationoptions.imagesfolder = _imagesfolder

    def classify(self):
        imagefiles = self.getfileslist()
        return self.process(imagefiles)

    def process(self, imagefiles):
        logging.info("Classifying...")
        results = {}
        engineholder = EngineHolder.getholder()
        # engine = engineholder.getengine()
        needrecognition = engineholder.getmodel().ClassifierType is not ClassifierTypeEnum.CT_Image
        if needrecognition:
            self.updaterecognizerparams(engineholder)
        filescount = len(imagefiles)
        for i in range(filescount):
            filepath = imagefiles[i]
            frdoc = engineholder.getengine().CreateFRDocument()
            frdoc.AddImageFile(filepath, None, None)
            if self.classificationoptions.correctorientation:
                logging.info("correcting orientation")
                frdoc.Preprocess(self.getpreprocessparams(engineholder),None, self.recognizerparams,None)
            if needrecognition:
                frdoc.Analyze(None, None, self.recognizerparams)
                frdoc.Recognize(None, None)
            newobject = engineholder.getclassificationengine().CreateObjectFromDocument(frdoc)
            classificationresults = engineholder.getmodel().Classify(newobject)
            categorylabel = classificationresults[0].CategoryLabel if classificationresults else ClassifiedImage.unknownclassname
            probability = classificationresults[0].Probability
            # for item in classificationresults:
            #     print("Classification results ", item)
            # classifiedimage = ClassifiedImage(filepath, categorylabel)
            filename = os.path.split(filepath)[1]
            logging.debug("{} : {} - {}".format(filename, categorylabel, probability))
            results[filename] = categorylabel + "-" + str(round(probability, 4)*100)
            # print("=================CLASSIFICATION RESULTS HERE==============", results)
            # self.postprocessing(engineholder, frdoc, results, i)
        return results

    def postprocessing(self,engingeholder, doc, results, i):
        logging.info("Post-Processing...")
        # doc.Process(results)
        # doc.Recognize(results,results)
        XCA_Ascii = 1
        FEF_XML = 7
        exportParams = engingeholder.getengine().CreateXMLExportParams()
        exportParams.WriteCharAttributes = XCA_Ascii

        rtfExportPath = "E:\\junk\\exported-{}.xml".format(i)

        doc.Export(rtfExportPath, FEF_XML, exportParams)


    def getfileslist(self):
        imagesfolder = self.classificationoptions.imagesfolder
        files = []
        for f in os.listdir(imagesfolder):
            files.append(os.path.join(imagesfolder,f))
        files.sort()
        result = []
        for file in files:
            name, ext = os.path.splitext(file)
            if ext.lower() not in self.supportedfiletypes:
                continue
            result.append(file)
        return result

    def getpreprocessparams(self, engineholder):
        if not self.preprocessparams:
            self.preprocessparams = engineholder.getengine().CreatePagePreprocessingParams()
        self.preprocessparams.CorrectOrientation = self.classificationoptions.correctorientation
        return self.preprocessparams

    def updaterecognizerparams(self, engineholder):
        if not self.recognizerparams:
            self.recognizerparams = engineholder.getengine().CreateRecognizerParams()
        languages = engineholder.getmodel().Languages
        languages_string = ""
        for i in range(len(languages)):
            if len(languages_string) > 0:
                languages_string += ","
            languages_string += languages[i]
        self.recognizerparams.SetPredefinedTextLanguage(languages_string)
