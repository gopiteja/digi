FROM apache_base

# Copy over the apache configuration file and enable the site
COPY ./excel_export_api.conf /etc/apache2/sites-available/excel_export_api.conf
COPY ./httpd.conf /etc/apache2/httpd.conf
RUN echo "Include /etc/apache2/httpd.conf" >> /etc/apache2/apache2.conf
COPY ./mpm_event.conf /etc/apache2/mods-available/mpm_event.conf

RUN a2ensite excel_export_api
RUN a2enmod headers

# Copy over the wsgi file
COPY ./excel_export_api.wsgi /var/www/excel_export_api/excel_export_api.wsgi

RUN chmod a+x /var/www/excel_export_api/excel_export_api.wsgi

COPY ./run.py /var/www/excel_export_api/run.py
COPY ./app /var/www/excel_export_api/app/

RUN a2dissite 000-default.conf
RUN a2ensite excel_export_api.conf

EXPOSE 80

WORKDIR /var/www/excel_export_api

CMD  /usr/sbin/apache2ctl -D FOREGROUND

