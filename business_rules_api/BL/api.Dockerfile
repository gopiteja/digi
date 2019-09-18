FROM apache_base

# Copy over the apache configuration file and enable the site
COPY ./business_rules_api.conf /etc/apache2/sites-available/business_rules_api.conf
COPY ./httpd.conf /etc/apache2/httpd.conf
RUN echo "Include /etc/apache2/httpd.conf" >> /etc/apache2/apache2.conf
COPY ./mpm_event.conf /etc/apache2/mods-available/mpm_event.conf

RUN a2ensite business_rules_api
RUN a2enmod headers

# Copy over the wsgi file
COPY ./business_rules_api.wsgi /var/www/business_rules_api/business_rules_api.wsgi

RUN chmod a+x /var/www/business_rules_api/business_rules_api.wsgi

COPY ./run.py /var/www/business_rules_api/run.py
COPY ./app /var/www/business_rules_api/app/

RUN a2dissite 000-default.conf
RUN a2ensite business_rules_api.conf

EXPOSE 80

WORKDIR /var/www/business_rules_api

RUN ln -sf /dev/stdout /var/log/apache2/access.log && \
    ln -sf /dev/stdout /var/log/apache2/error.log

CMD  /usr/sbin/apache2ctl -D FOREGROUND