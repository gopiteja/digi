FROM apache_base

# Copy over the apache configuration file and enable the site
COPY ./database_ingestion.conf /etc/apache2/sites-available/database_ingestion.conf
COPY ./httpd.conf /etc/apache2/httpd.conf
RUN echo "Include /etc/apache2/httpd.conf" >> /etc/apache2/apache2.conf
COPY ./mpm_event.conf /etc/apache2/mods-available/mpm_event.conf

RUN a2ensite database_ingestion
RUN a2enmod headers

# Copy over the wsgi file
COPY ./database_ingestion.wsgi /var/www/database_ingestion/database_ingestion.wsgi

RUN chmod a+x /var/www/database_ingestion/database_ingestion.wsgi

COPY ./run.py /var/www/database_ingestion/run.py
COPY ./app /var/www/database_ingestion/app/

RUN a2dissite 000-default.conf
RUN a2ensite database_ingestion.conf

EXPOSE 80

WORKDIR /var/www/database_ingestion

RUN apt-get install python3-mysql.connector

RUN ln -sf /dev/stdout /var/log/apache2/access.log && \
    ln -sf /dev/stdout /var/log/apache2/error.log

CMD  /usr/sbin/apache2ctl -D FOREGROUND
