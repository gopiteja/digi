import os.path
from PIL.BmpImagePlugin import BmpImageFile

class ClassifiedImage:
    unknownclassname = "Not Classified"
    filename = None
    category = None
    name = None
    bitmapimage = None

    def __init__(self,filename, category):
        self.filename = filename
        self.category = category
        self.name, ext = os.path.splitext(filename)

    def loadimage(self):
        if not self.bitmapimage:
            if not self.ispdf():
                self.bitmapimage = BmpImageFile(self.filename)
            else:
                pass

    def ispdf(self):
        return os.path.splitext(self.filename)[1].lower() == ".pdf"
