FROM apache_base

# Copy over the apache configuration file and enable the site
COPY ./user_management.conf /etc/apache2/sites-available/user_management.conf
COPY ./httpd.conf /etc/apache2/httpd.conf
RUN echo "Include /etc/apache2/httpd.conf" >> /etc/apache2/apache2.conf
COPY ./mpm_event.conf /etc/apache2/mods-available/mpm_event.conf

RUN a2ensite user_management
RUN a2enmod headers

# Copy over the wsgi file
COPY ./user_management.wsgi /var/www/user_management/user_management.wsgi

RUN chmod a+x /var/www/user_management/user_management.wsgi

COPY ./run.py /var/www/user_management/run.py
COPY ./app /var/www/user_management/app/

RUN a2dissite 000-default.conf
RUN a2ensite user_management.conf

EXPOSE 80

WORKDIR /var/www/user_management

RUN ln -sf /dev/stdout /var/log/apache2/access.log && \
    ln -sf /dev/stdout /var/log/apache2/error.log

CMD  /usr/sbin/apache2ctl -D FOREGROUND

