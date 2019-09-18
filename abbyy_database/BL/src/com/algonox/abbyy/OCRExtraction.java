package com.algonox.abbyy;

import java.util.Properties;

import com.abbyy.FREngine.XMLCharAttributesEnum;
import com.abbyy.FREngine.Engine;
import com.abbyy.FREngine.FileExportFormatEnum;
import com.abbyy.FREngine.IDocumentProcessingParams;
import com.abbyy.FREngine.IEngine;
import com.abbyy.FREngine.IFRDocument;
import com.algonox.abbyy.data.DataAccess;
import com.algonox.abbyy.stream.InputStream;
import com.algonox.abbyy.stream.OutputStream;
import com.abbyy.FREngine.IXMLExportParams;

public class OCRExtraction {

	private IEngine engine = null;
	public static Properties configProperties = new Properties();

	public static void main(String[] args) {
		OCRExtraction extraction = new OCRExtraction();

		try {
		//	System.out.println("Start "+System.currentTimeMillis());
			java.io.InputStream inputStream = extraction.getClass().getClassLoader()
					.getResourceAsStream("config.properties");

			configProperties.load(inputStream);
		//	System.out.println("loaded properties"+System.currentTimeMillis());
			String fileId = (args[0]);
			extraction.loadEngine();
		//	System.out.println("loaded loaded engine"+System.currentTimeMillis());
			// Setup FREngine
			extraction.setupFREngine();
			// Process sample image
		//	System.out.println("started processing"+System.currentTimeMillis());
			extraction.processImage(fileId);
		//	System.out.println("completed processing"+System.currentTimeMillis());
		} catch (Exception e) {
			System.out.println("ERROR:");
			e.printStackTrace();
		} finally {
			// Unload ABBYY FineReader Engine
			try {
				extraction.unloadEngine();
			} catch (Exception e) {
				//hide the exception
			}
		}
	}

	private void processImage(String fileId) throws Exception {
		InputStream inputStream = null;
		OutputStream outputStream = null;
		IFRDocument ifrDoc = null;
		try {

			// Create document
			ifrDoc = engine.CreateFRDocument();
			IDocumentProcessingParams dpp = engine.CreateDocumentProcessingParams();
			DataAccess dataAccess = new DataAccess();
		//	System.out.println("Getting blob"+System.currentTimeMillis());
			byte[] fileData = dataAccess.getFileData(fileId);
		//	System.out.println("Got blob"+System.currentTimeMillis());
			inputStream = new InputStream(fileData);
			ifrDoc.AddImageFileFromStream(inputStream, null, null, null, "0");
			dpp.getPageProcessingParams().getRecognizerParams()
					.SetPredefinedTextLanguage(configProperties.getProperty("abbyy.language"));
			dpp.getPageProcessingParams().getObjectsExtractionParams().setEnableAggressiveTextExtraction(true);
			dpp.getPageProcessingParams().getObjectsExtractionParams().setDetectTextOnPictures(true);
		//	System.out.println("started process"+System.currentTimeMillis());
			ifrDoc.Process(null);
			//System.out.println("Stop processing"+System.currentTimeMillis());
			IXMLExportParams XMLParams = engine.CreateXMLExportParams();

			XMLParams.setWriteCharAttributes(XMLCharAttributesEnum.XCA_Basic);
			// Save results to pdf using 'balanced' scenario
			outputStream = new OutputStream();
		//	System.out.println("started export"+System.currentTimeMillis());
			ifrDoc.ExportToMemory(outputStream, FileExportFormatEnum.FEF_XML, XMLParams);
		//	System.out.println("Done export"+System.currentTimeMillis());

		} finally {
			// Close document
			if (inputStream != null)
				inputStream.Close();
			if (outputStream != null)
				outputStream.Close();
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
