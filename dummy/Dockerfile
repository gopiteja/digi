FROM ubuntu

RUN apt-get update
RUN apt-get install -y apt-utils vim curl apache2 apache2-utils
RUN apt-get -y install python3 libapache2-mod-wsgi-py3
RUN apt-get -y install libmariadbclient-dev
RUN apt-get install -y libsm6 libxext6 libxrender-dev
RUN ln /usr/bin/python3 /usr/bin/python
RUN apt-get -y install python3-pip
RUN ln /usr/bin/pip3 /usr/bin/pip
RUN apt-get update
RUN apt-get install -y libmagickwand-dev
# RUN apt-get install libmagickcore5-extra

COPY ./app/ /app/

# Install any needed packages specified in requirements.txt
COPY ./app/requirements.txt /app/
RUN cat /app/requirements.txt | xargs -n 1 pip install ; exit 0
RUN pip install scikit-image

COPY ./app/jinja2ext.py /usr/local/lib/python3.6/dist-packages/flask_cache

COPY ./app/db_utils.py /usr/lib/python3.6
COPY policy.xml /etc/ImageMagick-6
