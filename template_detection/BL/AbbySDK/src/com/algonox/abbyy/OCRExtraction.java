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
					.getResourceAsStream("resources/config.properties");
			configProperties.load(inputStream);
			String fileName = args[0];
			extraction.loadEngine();
			// Setup FREngine
			extraction.setupFREngine();
			// Process sample document
			extraction.processDoc(fileName);
		} catch (Exception e) {
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

	private String processImage(String fileName) throws Exception {
		/*
		 * InputStream inputStream = null; OutputStream outputStream = null;
		 */
		IFRDocument ifrDoc = null;
		String xml = null;
		try {

			// Create document
			ifrDoc = engine.CreateFRDocument();

			IDocumentProcessingParams dpp = engine.CreateDocumentProcessingParams();
			dpp.getPageProcessingParams().getPagePreprocessingParams().setCorrectOrientation(true);
			dpp.getPageProcessingParams().getPagePreprocessingParams().setCorrectInvertedImage(true);
			dpp.getPageProcessingParams().getPagePreprocessingParams()
					.setCorrectShadowsAndHighlights(ThreeStatePropertyValueEnum.TSPV_Yes);

			dpp.getPageProcessingParams().getRecognizerParams()
					.SetPredefinedTextLanguage(configProperties.getProperty("abbyy.language"));
			dpp.getPageProcessingParams().getRecognizerParams().setDetectTextTypesIndependently(true);
			dpp.getPageProcessingParams().getObjectsExtractionParams().setEnableAggressiveTextExtraction(true);
			dpp.getPageProcessingParams().getObjectsExtractionParams().setDetectTextOnPictures(true);

			ifrDoc.AddImageFile(fileName, null, null);
			ifrDoc.Process(dpp);

			IXMLExportParams xmlParams = engine.CreateXMLExportParams();
			xmlParams.setWriteCharAttributes(XMLCharAttributesEnum.XCA_Ascii);
			xmlParams.setWriteParagraphStyles(true);
			// Save results to pdf using 'balanced' scenario
			Path path = Paths.get(fileName);
			String outputFile = path.getParent()+File.separator+"x_"+path.getFileName();
			
			ifrDoc.Export(outputFile, FileExportFormatEnum.FEF_XML, xmlParams);
			byte[] encoded = Files.readAllBytes(Paths.get(outputFile));
			xml = new String(encoded, StandardCharsets.UTF_8);
		} catch (Exception e) {
			e.printStackTrace();
		}
		return xml;
	}

	private void processDoc(String fileName) throws Exception {
		
		IFRDocument ifrDoc = null;
		try {

			// Create document
			ifrDoc = engine.CreateFRDocument();
			
			IPrepareImageMode prepareImageMode = engine.CreatePrepareImageMode();
			prepareImageMode.setCorrectSkew(true);
			prepareImageMode.setCorrectSkewMode(CorrectSkewModeEnum.CSM_CorrectSkewByHorizontalText.getValue());
			
			IDocumentProcessingParams dpp = engine.CreateDocumentProcessingParams();
			dpp.getPageProcessingParams().getPagePreprocessingParams().setCorrectOrientation(true);
			dpp.getPageProcessingParams().getPagePreprocessingParams().setCorrectInvertedImage(true);
			
			dpp.getPageProcessingParams().getRecognizerParams()
			.SetPredefinedTextLanguage(configProperties.getProperty("abbyy.language"));
			dpp.getPageProcessingParams().getObjectsExtractionParams().setEnableAggressiveTextExtraction(true);
			dpp.getPageProcessingParams().getObjectsExtractionParams().setDetectTextOnPictures(true);
	
			ifrDoc.AddImageFile(fileName, prepareImageMode, null);
			ifrDoc.Process(dpp);

			IPDFExportParams pdfParams = engine.CreatePDFExportParams();
			pdfParams.setScenario(PDFExportScenarioEnum.PES_Balanced);
			// Save results to pdf using 'balanced' scenario
			Path path = Paths.get(fileName);
			String outputFile = path.getParent()+File.separator+"o_"+path.getFileName();
			ifrDoc.Export(outputFile, FileExportFormatEnum.FEF_PDF, pdfParams);
			
			java.io.InputStream finput = new FileInputStream(fileName);
			byte[] imageBytes = new byte[(int)fileName.length()];
			finput.read(imageBytes, 0, imageBytes.length);
			finput.close();
			String imageStr = Base64.getEncoder().encodeToString(imageBytes);
			
			String xml_string = processImage(outputFile);
			System.out.println("{'blob': "+imageStr+", 'xml_string':"+ xml_string+"}");

		} finally {
			
			if (ifrDoc != null)
				ifrDoc.Close();
		}

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
