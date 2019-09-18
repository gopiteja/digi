FROM apache_base

# Copy over the apache configuration file and enable the site
COPY ./button_functions.conf /etc/apache2/sites-available/button_functions.conf
COPY ./httpd.conf /etc/apache2/httpd.conf
RUN echo "Include /etc/apache2/httpd.conf" >> /etc/apache2/apache2.conf
COPY ./mpm_event.conf /etc/apache2/mods-available/mpm_event.conf

RUN a2ensite button_functions
RUN a2enmod headers

# Copy over the wsgi file
COPY ./button_functions.wsgi /var/www/button_functions/button_functions.wsgi

RUN chmod a+x /var/www/button_functions/button_functions.wsgi

COPY ./run.py /var/www/button_functions/run.py
COPY ./app /var/www/button_functions/app/

RUN a2dissite 000-default.conf
RUN a2ensite button_functions.conf

EXPOSE 80

WORKDIR /var/www/button_functions

RUN ln -sf /dev/stdout /var/log/apache2/access.log && \
    ln -sf /dev/stdout /var/log/apache2/error.log

CMD  /usr/sbin/apache2ctl -D FOREGROUND
