#! /bin/sh
javac -classpath "src/.:libs/abbyy.FREngine.jar:libs/mysql-connector-java-8.0.17.jar" -d bin src/com/algonox/abbyy/data/*.java
javac -classpath "src/.:libs/abbyy.FREngine.jar:libs/mysql-connector-java-8.0.17.jar" -d bin src/com/algonox/abbyy/stream/*.java
javac -classpath "src/.:libs/abbyy.FREngine.jar:libs/mysql-connector-java-8.0.17.jar" -d bin src/com/algonox/abbyy/*.java
