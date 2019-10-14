FROM apache_base

# Sets the working directory for following COPY and CMD instructions
# Notice we haven’t created a directory by this name - this
# instruction creates a directory with this name if it doesn’t exist
WORKDIR /app

# Copy rest of the files
COPY . /app/

RUN pip install schedule

USER root

# 1. OS
# Retrieve new lists of packages
ENV OS_REFRESHED_AT 2017-04-21
RUN apt-get -qq update # -qq -- no output except for errors

# 2. APT
# Install g++, nano, pigz, wget
ENV APT_REFRESHED_AT 2017-04-21
RUN apt-get -qq update \
        && apt-get install -y g++ nano pigz wget \
        && apt-get clean

# 3. JAVA
# Install java
ENV JAVA_REFRESHED_AT 2017-04-21
RUN apt-get -qq update && apt-get install -y openjdk-8* && apt-get clean

# 5. SPARK
# Download Apache Spark ver. 2.1.0 (2016-12-28) to '/tmp' directory
ENV URL_SCHEME=http
ENV URL_NETLOC=d3kbcqa49mib13.cloudfront.net
ENV URL_PATH=/spark-2.1.0-bin-hadoop2.7.tgz
ENV URL=$URL_SCHEME://$URL_NETLOC$URL_PATH
RUN wget --directory-prefix /tmp $URL
# Unpack '/tmp/spark-2.1.0-bin-hadoop2.7.tgz' archive
RUN unpigz --to-stdout /tmp/spark-2.1.0-bin-hadoop2.7.tgz \
        | tar --extract --file - --directory /usr/local/src
# Remove '/tmp/spark-2.1.0-bin-hadoop2.7.tgz' archive
RUN rm /tmp/spark-2.1.0-bin-hadoop2.7.tgz
# Set up Apache Spark
ENV SPARK_HOME=/usr/local/src/spark-2.1.0-bin-hadoop2.7
ENV PYTHON_DIR_PATH=$SPARK_HOME/python/
ENV PY4J_PATH=$SPARK_HOME/python/lib/py4j-0.10.4-src.zip
ENV PYTHONPATH=$PYTHON_DIR_PATH:$PY4J_PATH
COPY log4j.properties $SPARK_HOME/conf/log4j.properties
COPY spark-defaults.conf $SPARK_HOME/conf/spark-defaults.conf

WORKDIR /home/pyspark

RUN wget https://dev.mysql.com/get/Downloads/Connector-J/mysql-connector-java_8.0.17-1ubuntu18.04_all.deb
RUN dpkg-deb -x mysql-connector-java_8.0.17-1ubuntu18.04_all.deb $SPARK_HOME/jars
RUN pip install pyspark
# RUN cp -i $SPARK_HOME/mysql-connector-java-8.0.17.jar $SPARK_HOME/jars

WORKDIR /app
# Run app.py when the container launches
CMD ["python", "-u", "Recon.py"]