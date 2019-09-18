FROM apache_base

# Copy over the apache configuration file and enable the site
COPY ./table_merger_api.conf /etc/apache2/sites-available/table_merger_api.conf
COPY ./httpd.conf /etc/apache2/httpd.conf
RUN echo "Include /etc/apache2/httpd.conf" >> /etc/apache2/apache2.conf
COPY ./mpm_event.conf /etc/apache2/mods-available/mpm_event.conf

RUN a2ensite table_merger_api
RUN a2enmod headers

# Copy over the wsgi file
COPY ./table_merger_api.wsgi /var/www/table_merger_api/table_merger_api.wsgi

RUN chmod a+x /var/www/table_merger_api/table_merger_api.wsgi

COPY ./run.py /var/www/table_merger_api/run.py
COPY ./app /var/www/table_merger_api/app/

RUN a2dissite 000-default.conf
RUN a2ensite table_merger_api.conf

EXPOSE 80

WORKDIR /var/www/table_merger_api

CMD  /usr/sbin/apache2ctl -D FOREGROUND

