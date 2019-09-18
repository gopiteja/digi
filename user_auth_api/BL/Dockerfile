FROM apache_base

# Copy over the apache configuration file and enable the site
COPY ./user_auth_api.conf /etc/apache2/sites-available/user_auth_api.conf
COPY ./httpd.conf /etc/apache2/httpd.conf
RUN echo "Include /etc/apache2/httpd.conf" >> /etc/apache2/apache2.conf
COPY ./mpm_event.conf /etc/apache2/mods-available/mpm_event.conf

RUN a2ensite user_auth_api
RUN a2enmod headers

# Copy over the wsgi file
COPY ./user_auth_api.wsgi /var/www/user_auth_api/user_auth_api.wsgi

RUN chmod a+x /var/www/user_auth_api/user_auth_api.wsgi

COPY ./run.py /var/www/user_auth_api/run.py
COPY ./app /var/www/user_auth_api/app/

RUN a2dissite 000-default.conf
RUN a2ensite user_auth_api.conf

EXPOSE 80

WORKDIR /var/www/user_auth_api

RUN ln -sf /dev/stdout /var/log/apache2/access.log && \
    ln -sf /dev/stdout /var/log/apache2/error.log

CMD  /usr/sbin/apache2ctl -D FOREGROUND

