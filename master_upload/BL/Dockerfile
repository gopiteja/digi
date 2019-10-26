FROM apache_base

# Copy over the apache configuration file and enable the site
COPY ./master_upload.conf /etc/apache2/sites-available/master_upload.conf
COPY ./httpd.conf /etc/apache2/httpd.conf
RUN echo "Include /etc/apache2/httpd.conf" >> /etc/apache2/apache2.conf
COPY ./mpm_event.conf /etc/apache2/mods-available/mpm_event.conf

RUN a2ensite master_upload
RUN a2enmod headers

# Copy over the wsgi file
COPY ./master_upload.wsgi /var/www/master_upload/master_upload.wsgi

RUN chmod a+x /var/www/master_upload/master_upload.wsgi

COPY ./run.py /var/www/master_upload/run.py
COPY ./app /var/www/master_upload/app/

RUN a2dissite 000-default.conf
RUN a2ensite master_upload.conf

EXPOSE 80

WORKDIR /var/www/master_upload

RUN ln -sf /dev/stdout /var/log/apache2/access.log && \
    ln -sf /dev/stdout /var/log/apache2/error.log

CMD  /usr/sbin/apache2ctl -D FOREGROUND

