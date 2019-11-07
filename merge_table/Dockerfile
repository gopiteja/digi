FROM apache_base

# Copy over the apache configuration file and enable the site
COPY ./merge_table.conf /etc/apache2/sites-available/merge_table.conf
COPY ./httpd.conf /etc/apache2/httpd.conf
RUN echo "Include /etc/apache2/httpd.conf" >> /etc/apache2/apache2.conf
COPY ./mpm_event.conf /etc/apache2/mods-available/mpm_event.conf

# COPY ./ports.conf /etc/apache2/ports.conf
RUN a2ensite merge_table
RUN a2enmod headers

# Copy over the wsgi file
COPY ./merge_table.wsgi /var/www/merge_table/merge_table.wsgi

RUN chmod a+x /var/www/merge_table/merge_table.wsgi


COPY ./run.py /var/www/merge_table/run.py
COPY ./app /var/www/merge_table/app/

RUN a2dissite 000-default.conf
RUN a2ensite merge_table.conf

EXPOSE 80

WORKDIR /var/www/merge_table

RUN ln -sf /dev/stdout /var/log/apache2/access.log && \
    ln -sf /dev/stdout /var/log/apache2/error.log

CMD  /usr/sbin/apache2ctl -D FOREGROUND
