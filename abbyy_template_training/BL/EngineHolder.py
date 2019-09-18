import comtypes.client as cc
import FREConfig
from ace_logger import Logging
logging = Logging()

# class Singleton(type):
#     # def __init__(cls, name, bases, attrs, **kwargs):
#     #     super().__init__(name, bases, attrs)
#     #     cls._instance = None
#
#     def __call__(cls, *args, **kwargs):
#         if cls._instance is None:
#             cls._instance = super().__call__(*args, **kwargs)
#         return cls._instance

#  Singleton class


class EngineHolder:
    engineLoader = None
    engine = None
    classificationEngine = None
    model = None
    instance = None

    @staticmethod
    def getholder():
        if not EngineHolder.instance:
            EngineHolder()
            EngineHolder.instance.loadengine()
            EngineHolder.instance.loadwithprofile("TextExtraction_Accuracy")
        return EngineHolder.instance

    def __init__(self):
        if not EngineHolder.instance:
            EngineHolder.instance = self
        else:
            raise Exception("Cannot instantiate EngineHolder again")

    def loadengine(self):
        if not self.instance.engineLoader:
            self.instance.engineLoader = cc.CreateObject("FREngine.OutprocLoader")
        if not self.instance.engine:
            self.instance.engine = self.instance.engineLoader.InitializeEngine(FREConfig.GetCustomerProjectId(), FREConfig.GetLicensePath(), FREConfig.GetLicensePassword(), "", "",
                                               False)

    def loadwithprofile(self, profile):
        self.getengine().LoadPredefinedProfile( profile )
        # Possible profile names are:
        # "DocumentConversion_Accuracy", "DocumentConversion_Speed",
        # "DocumentArchiving_Accuracy", "DocumentArchiving_Speed",
        # "BookArchiving_Accuracy", "BookArchiving_Speed",
        # "TextExtraction_Accuracy", "TextExtraction_Speed",
        # "FieldLevelRecognition",
        # "BarcodeRecognition_Accuracy", "BarcodeRecognition_Speed",
        # "HighCompressedImageOnlyPdf",
        # "BusinessCardsProcessing",
        # "EngineeringDrawingsProcessing",
        # "Version9Compatibility",
        # "Default"

    def getengine(self):
        if not self.instance.engine:
            self.instance.loadengine()
        return self.instance.engine

    def getclassificationengine(self):
        if not self.instance.classificationEngine:
            self.instance.classificationEngine = self.instance.engine.CreateClassificationEngine()
        return self.instance.classificationEngine

    def getmodel(self):
        return self.instance.model

    def setmodel(self, _model):
        self.model = _model

    def unloadengine(self):
        logging.info("Deinitializing Engine...")
        self.instance.engine = None
        self.instance.classificationEngine = None
        self.instance.engineLoader.ExplicitlyUnload()
        self.instance.engineLoader = None
        self.instance = None

