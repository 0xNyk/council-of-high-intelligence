FROM nginx:1.27-alpine

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY site/index.html /usr/share/nginx/html/index.html
COPY README.md /usr/share/nginx/html/README.md
COPY LICENSE /usr/share/nginx/html/LICENSE
COPY install.sh /usr/share/nginx/html/install.sh
COPY assets /usr/share/nginx/html/assets

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
