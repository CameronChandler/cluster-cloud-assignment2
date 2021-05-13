# Assumes the build context is the root of the project
from nginx:latest
copy config/couch.conf /etc/nginx/conf.d/sites-available/couch.conf
run mkdir -p /etc/nginx/conf.d/sites-enabled
run ln -s /etc/nginx/conf.d/sites-available/couch.conf /etc/nginx/conf.d/sites-enabled/couch.conf
copy config/nginx.conf /etc/nginx/nginx.conf
copy certs /etc/ssl/private
copy frontend /etc/share/nginx/html