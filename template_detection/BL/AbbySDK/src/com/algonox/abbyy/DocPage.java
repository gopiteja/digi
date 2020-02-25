package com.algonox.abbyy;

import com.abbyy.FREngine.RotationTypeEnum;
import org.json.simple.JSONObject;

public class DocPage {

	private RotationTypeEnum rotate;
	private int pageNum;

	

	public RotationTypeEnum getRotate() {
		return rotate;
	}

	public void setRotate(RotationTypeEnum rotate) {
		this.rotate = rotate;
	}

	public int getPageNum() {
		return pageNum;
	}

	public void setPageNum(int pageNum) {
		this.pageNum = pageNum;
	}

	public static DocPage parse(JSONObject json) {
		DocPage docPage = new DocPage();
		int rotate = ((Long)json.get("rotate")).intValue();
		if(rotate==90) {
			docPage.setRotate(RotationTypeEnum.RT_Clockwise);
		}else if(rotate==-90) {
			docPage.setRotate(RotationTypeEnum.RT_Counterclockwise);
		}
		else if(rotate==180) {
			docPage.setRotate(RotationTypeEnum.RT_Upsidedown);
		}
		
		docPage.setPageNum(((Long)json.get("pageNum")).intValue());
		return docPage;

	}
}
