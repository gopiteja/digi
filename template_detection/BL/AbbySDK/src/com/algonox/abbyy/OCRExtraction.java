package com.algonox.abbyy;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;

import com.abbyy.FREngine.CorrectSkewModeEnum;
import com.abbyy.FREngine.Engine;
import com.abbyy.FREngine.FileExportFormatEnum;
import com.abbyy.FREngine.IDocumentProcessingParams;
import com.abbyy.FREngine.IEngine;
import com.abbyy.FREngine.IFRDocument;
import com.abbyy.FREngine.IFRPages;
import com.abbyy.FREngine.IImageDocument;
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
			JSONParser parser = new JSONParser();
			java.io.InputStream inputStream = extraction.getClass().getClassLoader()
					.getResourceAsStream("config.properties");
			configProperties.load(inputStream);
			String json = args[0];
			String fileName = null;
			List<DocPage> pages = null;
			try {
			    System.out.println(json);
				JSONObject jsonObj = (JSONObject) parser.parse(json);
				fileName = (String) jsonObj.get("fileName");
				Object obj = jsonObj.get("pages");
				
				if (obj != null) {
					JSONArray array = (JSONArray) obj;
					pages = new ArrayList<DocPage>();
					for (int i = 0; i < array.size(); i++) {
						pages.add(DocPage.parse((JSONObject) array.get(i)));
					}
				}
			}catch(Exception e) {
				fileName = json;
			}
			

			extraction.loadEngine();
			// Setup FREngine
			extraction.setupFREngine();
			// Process sample document
			extraction.processDoc(fileName, pages);
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

	/*
	 * private String processImage(String fileName) throws Exception {
	 * 
	 * InputStream inputStream = null; OutputStream outputStream = null;
	 * 
	 * IFRDocument ifrDoc = null; String xml = null; try {
	 * 
	 * // Create document ifrDoc = engine.CreateFRDocument();
	 * 
	 * IDocumentProcessingParams dpp = engine.CreateDocumentProcessingParams();
	 * dpp.getPageProcessingParams().getPagePreprocessingParams().
	 * setCorrectOrientation(true);
	 * dpp.getPageProcessingParams().getPagePreprocessingParams().
	 * setCorrectInvertedImage(true);
	 * dpp.getPageProcessingParams().getPagePreprocessingParams()
	 * .setCorrectShadowsAndHighlights(ThreeStatePropertyValueEnum.TSPV_Yes);
	 * 
	 * dpp.getPageProcessingParams().getRecognizerParams()
	 * .SetPredefinedTextLanguage(configProperties.getProperty("abbyy.language"));
	 * dpp.getPageProcessingParams().getRecognizerParams().
	 * setDetectTextTypesIndependently(true);
	 * dpp.getPageProcessingParams().getObjectsExtractionParams().
	 * setEnableAggressiveTextExtraction(true);
	 * dpp.getPageProcessingParams().getObjectsExtractionParams().
	 * setDetectTextOnPictures(true);
	 * 
	 * ifrDoc.AddImageFile(fileName, null, null); ifrDoc.Process(dpp);
	 * 
	 * IXMLExportParams xmlParams = engine.CreateXMLExportParams();
	 * xmlParams.setWriteCharAttributes(XMLCharAttributesEnum.XCA_Ascii);
	 * xmlParams.setWriteParagraphStyles(true); // Save results to pdf using
	 * 'balanced' scenario Path path = Paths.get(fileName); String outputFile =
	 * path.getParent() + File.separator + "x_" + path.getFileName();
	 * 
	 * ifrDoc.Export(outputFile, FileExportFormatEnum.FEF_XML, xmlParams); byte[]
	 * encoded = Files.readAllBytes(Paths.get(outputFile)); xml = new
	 * String(encoded, StandardCharsets.UTF_8); } catch (Exception e) {
	 * e.printStackTrace(); } return xml; }
	 */

	private void processDoc(String fileName, List<DocPage> pages) throws Exception {

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
			dpp.getPageProcessingParams().getPagePreprocessingParams()
					.setCorrectShadowsAndHighlights(ThreeStatePropertyValueEnum.TSPV_Yes);

			dpp.getPageProcessingParams().getRecognizerParams()
					.SetPredefinedTextLanguage(configProperties.getProperty("abbyy.language"));
			dpp.getPageProcessingParams().getObjectsExtractionParams().setEnableAggressiveTextExtraction(true);
			dpp.getPageProcessingParams().getObjectsExtractionParams().setDetectTextOnPictures(true);

			ifrDoc.AddImageFile(fileName, prepareImageMode, null);
			// if pages details are provided
			if (pages != null) {
				IFRPages imgPages = ifrDoc.getPages();
				for (int i = 0; i < pages.size(); i++) {
					if (i < imgPages.getCount()) {
						IImageDocument imgDoc = ifrDoc.getPages().getElement(pages.get(i).getPageNum())
								.getImageDocument();
						imgDoc.Transform(pages.get(i).getRotate(), false, false);
					}
				}
			}
			ifrDoc.Process(dpp);

			IPDFExportParams pdfParams = engine.CreatePDFExportParams();
			pdfParams.setScenario(PDFExportScenarioEnum.PES_Balanced);
			// Save results to pdf using 'balanced' scenario
			//Path path = Paths.get(fileName);
			//String outputFile = path.getParent() + File.separator + "x_" + path.getFileName();
			ifrDoc.Export(fileName, FileExportFormatEnum.FEF_PDF, pdfParams);
			
			IXMLExportParams xmlParams = engine.CreateXMLExportParams();
			xmlParams.setWriteCharAttributes(XMLCharAttributesEnum.XCA_Ascii);
			xmlParams.setWriteParagraphStyles(true);
			ByteArrayOutputStream byteStream = new ByteArrayOutputStream();
			MemoryWriter writer = new MemoryWriter(byteStream);
			// Save results to xml using 'balanced' scenario
			ifrDoc.ExportToMemory(writer, FileExportFormatEnum.FEF_XML, xmlParams);
			String xml = new String(byteStream.toByteArray(), StandardCharsets.UTF_8);

//			String xml_string = processImage(outputFile);
// 			System.out.println("{'blob': "+imageStr+", 'xml_string':"+ xml_string+"}");
			System.out.println(xml);
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
