call Env.cmd
"%JDK%\bin\java" -classpath ".;src\.;lib\abbyy.FREngine.jar;lib\mysql-connector-java-8.0.17.jar" com.algonox.abbyy.OCRExtraction %1
pause
