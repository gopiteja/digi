package com.algonox.abbyy;

import java.io.IOException;
import java.io.OutputStream;

import com.abbyy.FREngine.IFileWriter;
import com.abbyy.FREngine.Ref;

public class MemoryWriter implements IFileWriter{
	
	OutputStream writer = null;
	
	public MemoryWriter(OutputStream writer) {
		this.writer=writer;
	}
	
	public void Write( byte[] data )
	{
		try {
			writer.write( data, 0, data.length);
		} catch (IOException e) {
			// TODO Auto-generated catch block
			//e.printStackTrace();
		}
	}
	
	public void Close()
	{
		try {
			writer.close();
		}catch(Exception e) {//supress error
			
		}
	}
	@Override
	public void Open(String arg0, Ref<Integer> arg1) {
		
		
	}
}

