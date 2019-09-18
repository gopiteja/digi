package com.algonox.abbyy.data;

import java.sql.Blob;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

import com.algonox.abbyy.OCRExtraction;

public class DataAccess {

	private String userName = OCRExtraction.configProperties.getProperty("database.username");
	private String passwd = OCRExtraction.configProperties.getProperty("database.paswd");
	private String databaseName = OCRExtraction.configProperties.getProperty("database.DBName");

	public byte[] getFileData(String fileId) throws Exception{

		ResultSet rs = null;
		byte[] blobAsBytes = null;
		Connection conn = null;

		try {
			conn = this.getConnection();
			PreparedStatement pstmt = conn
					.prepareStatement(OCRExtraction.configProperties.getProperty("database.blob.query"));
			pstmt.setString(1, fileId);
			rs = pstmt.executeQuery();

			while (rs.next()) {
				Blob dataAsBlob = rs.getBlob(OCRExtraction.configProperties.getProperty("database.blob.column"));
				int blobLength = (int) dataAsBlob.length();
				blobAsBytes = dataAsBlob.getBytes(1, blobLength);
			}
		} finally {
			try {
				if (rs != null) {
					rs.close();
				}
				if(conn!=null) {
					conn.close();
				}
			} catch (SQLException e) {
				//hide the exception
			}
		}
		return blobAsBytes;
	}

	private Connection getConnection() throws Exception {
		return DriverManager.getConnection(
				"jdbc:mysql://" + OCRExtraction.configProperties.getProperty("database.url") + "/" + databaseName,
				userName, passwd);
	}
}
