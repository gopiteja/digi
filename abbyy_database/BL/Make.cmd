call Env.cmd
"%JDK%\bin\Javac" -classpath "src\.;lib\abbyy.FREngine.jar;lib\mysql-connector-java-8.0.17.jar" src\com\algonox\abbyy\data\*.java
"%JDK%\bin\Javac" -classpath "src\.;lib\abbyy.FREngine.jar;lib\mysql-connector-java-8.0.17.jar" src\com\algonox\abbyy\stream\*.java
"%JDK%\bin\Javac" -classpath "src\.;lib\abbyy.FREngine.jar;lib\mysql-connector-java-8.0.17.jar" src\com\algonox\abbyy\*.java


pause
