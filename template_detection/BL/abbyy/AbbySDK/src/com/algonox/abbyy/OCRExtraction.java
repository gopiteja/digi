package com.algonox.abbyy;

import java.io.File;
import java.io.FileInputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Base64;
import java.util.Properties;

import com.abbyy.FREngine.CorrectSkewModeEnum;
import com.abbyy.FREngine.Engine;
import com.abbyy.FREngine.FileExportFormatEnum;
import com.abbyy.FREngine.IBarcodeParams;
import com.abbyy.FREngine.IDocumentProcessingParams;
import com.abbyy.FREngine.IEngine;
import com.abbyy.FREngine.IFRDocument;
import com.abbyy.FREngine.IPDFExportParams;
import com.abbyy.FREngine.IPrepareImageMode;
import com.abbyy.FREngine.IXMLExportParams;
import com.abbyy.FREngine.PDFExportScenarioEnum;
import com.abbyy.FREngine.ThreeStatePropertyValueEnum;
import com.abbyy.FREngine.XMLCharAttributesEnum;

public class OCRExtraction {

	private IEngine engine = null;
	public static Properties configProperties = new Properties();

	public static void main(String[] args) {
		OCRExtraction extraction = new OCRExtraction();
		try {
			java.io.InputStream inputStream = extraction.getClass().getClassLoader()
					.getResourceAsStream("config.properties");
			configProperties.load(inputStream);
			//String fileName = "y:\\img_4-20-2019_16-4-1-147.pdf";
			String fileName = args[0];
			//if(args.length>1) {
			//	barcode = args[1];
			//}
			
			extraction.loadEngine();
			// Setup FREngine
			extraction.setupFREngine();
			// Process sample document
			extraction.processDoc(fileName);
		} catch (Exception e) {
			System.out.println("ERROR:");
			e.printStackTrace();
		} catch (Error e) {
			System.out.println("ERROR:");
			e.printStackTrace();
		} finally {
			// Unload ABBYY FineReader Engine
			try {
				extraction.unloadEngine();
			} catch (Exception e) {
				// hide the exception
			}
		}
	}

	

	private void processDoc(String fileName) throws Exception {
		
		IFRDocument ifrDoc = null;
		
		try {
			ifrDoc = engine.CreateFRDocument();

				
				IPrepareImageMode prepareImageMode = engine.CreatePrepareImageMode();
				prepareImageMode.setCorrectSkew(true);
				prepareImageMode.setCorrectSkewMode(CorrectSkewModeEnum.CSM_CorrectSkewByHorizontalText.getValue());
				
				IDocumentProcessingParams dpp = engine.CreateDocumentProcessingParams();
				dpp.getPageProcessingParams().getPagePreprocessingParams().setCorrectOrientation(true);
				dpp.getPageProcessingParams().getPagePreprocessingParams().setCorrectInvertedImage(true);
				
				dpp.getPageProcessingParams().getRecognizerParams()
				.SetPredefinedTextLanguage(configProperties.getProperty("abbyy.language"));
				dpp.getPageProcessingParams().getObjectsExtractionParams().setDetectPorousText(false);
				
				dpp.getPageProcessingParams().getPageAnalysisParams().setDetectBarcodes(true);
				
				ifrDoc.AddImageFile(fileName, prepareImageMode, null);
				ifrDoc.Process(dpp);
				
				Path path = Paths.get(fileName);

				IPDFExportParams pdfParams = engine.CreatePDFExportParams();
				pdfParams.setScenario(PDFExportScenarioEnum.PES_Balanced);
				// Save results to pdf using 'balanced' scenario
				String outputFile = path.getParent()+File.separator+"o_"+path.getFileName();
				ifrDoc.Export(outputFile, FileExportFormatEnum.FEF_PDF, pdfParams);
				String imageStr = getBolbString(outputFile);
				
				IXMLExportParams xmlParams = engine.CreateXMLExportParams();
				xmlParams.setWriteCharAttributes(XMLCharAttributesEnum.XCA_Ascii);
				xmlParams.setWriteParagraphStyles(true);
				// Save results to pdf using 'balanced' scenario
				outputFile = path.getParent()+File.separator+"x_"+path.getFileName();
				ifrDoc.Export(outputFile, FileExportFormatEnum.FEF_XML, xmlParams);
				byte[] encoded = Files.readAllBytes(Paths.get(outputFile));
				String xml_string = new String(encoded, StandardCharsets.UTF_8);
				
				System.out.println(xml_string);
				System.out.println(encoded);

		} finally {
			
			if (ifrDoc != null)
				ifrDoc.Close();
		}

	}

	private String getBolbString(String fileName) throws Exception{
		java.io.InputStream finput = new FileInputStream(fileName);
		byte[] imageBytes = new byte[(int)fileName.length()];
		finput.read(imageBytes, 0, imageBytes.length);
		finput.close();
		return Base64.getEncoder().encodeToString(imageBytes);
	}
	private void unloadEngine() throws Exception {
		engine = null;
		Engine.DeinitializeEngine();
	}

	private void loadEngine() throws Exception {

		engine = Engine.InitializeEngine(configProperties.getProperty("abbyy.dll"),
				configProperties.getProperty("abbyy.customer.projectid"),
				configProperties.getProperty("abbyy.license.path"),
				configProperties.getProperty("abbyy.license.password"), "", "", false);
	}

	private void setupFREngine() {
		
		engine.LoadPredefinedProfile("TextExtraction_Accuracy");
		
		//engine.LoadPredefinedProfile("BarcodeRecognition_Accuracy"); 
		//if(barcode==null)
			//engine.LoadPredefinedProfile("TextExtraction_Accuracy");
		//else {
		//	engine.LoadPredefinedProfile("BarcodeRecognition_Accuracy");
		//}
		// Possible profile names are:
		// "DocumentConversion_Accuracy", "DocumentConversion_Speed",
		// "DocumentArchiving_Accuracy", "DocumentArchiving_Speed",
		// "BookArchiving_Accuracy", "BookArchiving_Speed",
		// "TextExtraction_Accuracy", "TextExtraction_Speed",
		// "FieldLevelRecognition",
		// "BarcodeRecognition_Accuracy", "BarcodeRecognition_Speed",
		// "HighCompressedImageOnlyPdf",
		// "BusinessCardsProcessing",
		// "EngineeringDrawingsProcessing",
		// "Version9Compatibility",
		// "Default"
	}
}
