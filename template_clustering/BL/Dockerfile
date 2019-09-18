FROM apache_base

# Copy over the apache configuration file and enable the site
COPY ./clustering.conf /etc/apache2/sites-available/clustering.conf
COPY ./httpd.conf /etc/apache2/httpd.conf
RUN echo "Include /etc/apache2/httpd.conf" >> /etc/apache2/apache2.conf
COPY ./mpm_event.conf /etc/apache2/mods-available/mpm_event.conf

RUN a2ensite clustering
RUN a2enmod headers

# Copy over the wsgi file
COPY ./clustering.wsgi /var/www/clustering/clustering.wsgi

RUN chmod a+x /var/www/clustering/clustering.wsgi

COPY ./run.py /var/www/clustering/run.py
COPY ./app /var/www/clustering/app/

RUN a2dissite 000-default.conf
RUN a2ensite clustering.conf

EXPOSE 80

WORKDIR /var/www/clustering

RUN ln -sf /dev/stdout /var/log/apache2/access.log && \
    ln -sf /dev/stdout /var/log/apache2/error.log

CMD  /usr/sbin/apache2ctl -D FOREGROUND

