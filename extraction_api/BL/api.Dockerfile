FROM apache_base

# Copy over the apache configuration file and enable the site
# RUN apt-get -y remove libapache2-mod-wsgi-py3
# RUN pip install -v mod_wsgi-httpd
# RUN pip install mod_wsgi
COPY ./extraction_api.conf /etc/apache2/sites-available/extraction_api.conf
COPY ./httpd.conf /etc/apache2/httpd.conf
RUN echo "Include /etc/apache2/httpd.conf" >> /etc/apache2/apache2.conf
COPY ./mpm_event.conf /etc/apache2/mods-available/mpm_event.conf

RUN a2ensite extraction_api
RUN a2enmod headers

# Copy over the wsgi file
COPY ./extraction_api.wsgi /var/www/extraction_api/extraction_api.wsgi

RUN chmod a+x /var/www/extraction_api/extraction_api.wsgi

COPY ./run.py /var/www/extraction_api/run.py
COPY ./app /var/www/extraction_api/app/

RUN a2dissite 000-default.conf
RUN a2ensite extraction_api.conf

EXPOSE 80

WORKDIR /var/www/extraction_api

RUN pip install matplotlib

RUN ln -sf /dev/stdout /var/log/apache2/access.log && \
    ln -sf /dev/stdout /var/log/apache2/error.log

CMD  /usr/sbin/apache2ctl -D FOREGROUND
