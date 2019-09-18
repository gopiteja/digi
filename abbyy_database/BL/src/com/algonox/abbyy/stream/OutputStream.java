package com.algonox.abbyy.stream;

import java.io.IOException;

import com.abbyy.FREngine.IFileWriter;
import com.abbyy.FREngine.Ref;

public class OutputStream implements IFileWriter {
	private java.io.OutputStream  stream = null;
	
	public OutputStream() throws Exception{
		stream = System.out;
	}

	@Override
	public void Close() {
		try {
			stream.flush();
			stream.close();
		} catch (IOException e) {
			//hide the exception
			System.out.println("ERROR:"+e.getMessage());
		}
		
	}

	@Override
	public void Open(String arg0, Ref<Integer> arg1) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void Write(byte[] arg0) {
		try {
			stream.write(arg0);
		} catch (IOException e) {
			//hide the exception
			System.out.println("ERROR:"+e.getMessage());
		}
		
	}
}
