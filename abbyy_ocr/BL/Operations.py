from EngineHolder import EngineHolder
from Trainer import ProcessingOptions
try:
    from .ace_logger import Logging
except:
    from ace_logger import Logging

logging = Logging()

class LoadModelOperation:
    filename = None

    def __init__(self, _filename):
        self.filename = _filename

    def getfilename(self):
        return self.filename

    def setfilename(self, filename):
        self.filename = filename

    def process(self):
        engineholder = EngineHolder.getholder()
        classengine = engineholder.getclassificationengine()
        engineholder.setmodel(classengine.CreateModelFromFile(self.filename))
        return engineholder.getmodel()


class AddImagesOperationData:
    def __init__(self, trainer, imageFiles, categoryName):
        self.ClassificationTrainer = trainer
        self.ImageFiles = imageFiles
        self.CategoryName = categoryName


class AddImagesOperation:
    def __init__(self,data):
        self.operationData = data

    def process(self):
        try:
            engineholder = EngineHolder.getholder()
            engine = engineholder.getengine()
            trainer = self.operationData.ClassificationTrainer
            index = trainer.gettrainingdata().Categories.Find(self.operationData.CategoryName)
            category = trainer.gettrainingdata().Categories[index]

            for i in range(len(self.operationData.ImageFiles)):
                filepath = self.operationData.ImageFiles[i]
                logging.info("Processing {} ...".format(filepath))
                frDoc = engine.CreateFRDocument()
                frDoc.AddImageFile(filepath,None,None)
                if ProcessingOptions.NeedRecognition:
                    frDoc.Analyze(None,None,trainer.getrecognizerparams())
                    frDoc.Recognize(None,None)
                newObject = engineholder.getclassificationengine().CreateObjectFromDocument(frDoc)
                newObject.Description = filepath
                category.Objects.Add(newObject)
            return True
        except Exception as e:
            logging.exception(f'{e}')
            return False
