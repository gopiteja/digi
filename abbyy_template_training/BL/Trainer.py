from enum import IntEnum
from EngineHolder import EngineHolder
from ClassifierTypeEnum import ClassifierTypeEnum
from ace_logger import Logging

logging = Logging().getLogger('ace')


class TrainingModeEnum(IntEnum):
    TM_Precision = 0,
    TM_Recall = 1,
    TM_Balanced = 2


class TrainingOptions:
    ClassifierType = ClassifierTypeEnum.CT_Combined  # Classifier type image or Text or combined
    TrainingMode = TrainingModeEnum.TM_Balanced  # training mode precision or recall or balanced
    AllowCrossValidation = True  # cross validation
    FoldsCount = 6  # folds count


class ProcessingOptions:
    Languages = "English"  # languages to recognize on images
    CorrectOrientation = False  # correct orientation
    NeedRecognition = True  # Recognize text on images


class Trainer:
    engineholder = None
    engine = None
    trainer = None
    trainingdata = None
    recognizerparams = None
    preprocessparams = None
    classificationengine = None
    processingoptions = ProcessingOptions()
    trainingoptions = TrainingOptions()

    def __init__(self):
        if not self.engineholder:
            self.engineholder = EngineHolder.getholder()
            self.engineholder.loadengine()

    def gettrainer(self):
        if not self.trainer:
            self.trainer = self.engineholder.getclassificationengine().CreateTrainer()
        return self.trainer

    def gettrainingdata(self):
        if not self.trainingdata:
            self.trainingdata = self.engineholder.getclassificationengine().CreateTrainingData()
        return self.trainingdata

    def savedata(self, filename):
        self.gettrainingdata().SaveToFile(filename)

    def loaddata(self, filename):
        self.gettrainingdata().LoadFromFile(filename)

    def updateprocessingparams(self):
        if not self.preprocessparams:
            self.preprocessparams = self.engineholder.getengine().CreatePagePreprocessingParams()
        self.preprocessparams.CorrectionOrientation = self.processingoptions.CorrectOrientation
        if not self.processingoptions.NeedRecognition:
            return
        if not self.recognizerparams:
            self.recognizerparams = self.engineholder.getengine().CreateRecognizerParams()
        self.recognizerparams.SetPredefinedTextLanguage(ProcessingOptions.Languages)

    def addcategory(self, categoryname):
        self.gettrainingdata().Categories.AddNew(categoryname)

    def getrecognizerparams(self):
        return self.recognizerparams

    def getimagefilesforcategory(self, categoryname):
        imagefiles = []
        index = self.gettrainingdata().Categories.Find(categoryname)
        allimageobjects = self.gettrainingdata().Categories[index].Objects
        for obj in allimageobjects:
            imagefiles.append(obj.Description)
        return imagefiles

    def train(self):
        logging.debug("Training...")
        self.gettrainer().TrainingParams.ClassifierType = self.trainingoptions.ClassifierType
        self.gettrainer().TrainingParams.TrainingMode = self.trainingoptions.TrainingMode
        self.gettrainer().ValidationParams.ShouldPerformValidation = self.trainingoptions.AllowCrossValidation
        self.gettrainer().ValidationParams.FoldsCount = self.trainingoptions.FoldsCount
        return self.gettrainer().TrainModel(self.trainingdata)
