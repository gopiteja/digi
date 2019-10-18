#!/bin/sh
export LD_LIBRARY_PATH=/opt/ABBYY/FREngine12/Bin/
java -classpath ".:bin/.:libs/abbyy.FREngine.jar:libs/mysql-connector-java-8.0.17.jar" com.algonox.abbyy.OCRExtraction $1
