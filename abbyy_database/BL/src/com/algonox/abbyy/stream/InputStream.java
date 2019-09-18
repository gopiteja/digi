package com.algonox.abbyy.stream;

import java.io.ByteArrayInputStream;
import java.io.IOException;

import com.abbyy.FREngine.IReadStream;
import com.abbyy.FREngine.Ref;

public class InputStream implements IReadStream {
	private ByteArrayInputStream fileBytes;

	public InputStream(byte[] fileBytes) {
		this.fileBytes = new ByteArrayInputStream(fileBytes);
	}

	public void Close() {
		try {
			fileBytes.close();
		} catch (IOException e) {
			// hide the exception
		}

	}

	public int Read(Ref<byte[]> ref, int count) {
		ref.set(new byte[count]);
		int result = fileBytes.read(ref.get(), 0, count);
		return (result == -1 ? 0 : result);
	}

}
