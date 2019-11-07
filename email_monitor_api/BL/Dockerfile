FROM apache_base

RUN pip install beautifulsoup4
RUN pip install email_reply_parser

# Copy over the apache configuration file and enable the site
COPY ./email_monitor_api.conf /etc/apache2/sites-available/email_monitor_api.conf
COPY ./httpd.conf /etc/apache2/httpd.conf
RUN echo "Include /etc/apache2/httpd.conf" >> /etc/apache2/apache2.conf
COPY ./mpm_event.conf /etc/apache2/mods-available/mpm_event.conf

RUN a2ensite email_monitor_api
RUN a2enmod headers

# Copy over the wsgi file
COPY ./email_monitor_api.wsgi /var/www/email_monitor_api/email_monitor_api.wsgi

RUN chmod a+x /var/www/email_monitor_api/email_monitor_api.wsgi

COPY ./run.py /var/www/email_monitor_api/run.py
COPY ./app /var/www/email_monitor_api/app/

RUN a2dissite 000-default.conf
RUN a2ensite email_monitor_api.conf

EXPOSE 80

WORKDIR /var/www/email_monitor_api
RUN chmod -R 777 /var/www

RUN ln -sf /dev/stdout /var/log/apache2/access.log && \
    ln -sf /dev/stdout /var/log/apache2/error.log

CMD  /usr/sbin/apache2ctl -D FOREGROUND

