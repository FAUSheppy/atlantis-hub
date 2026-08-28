FROM alpine

RUN apk add --no-cache py3-pip
RUN apk add --no-cache \
    cairo \
    cairo-dev \
    pango \
    gdk-pixbuf \
    libffi-dev

WORKDIR /app
RUN python3 -m pip install --no-cache-dir --break-system-packages waitress

COPY req.txt .
RUN python3 -m pip install --no-cache-dir --break-system-packages -r req.txt

COPY ./*.py .

RUN ln -s /app/uploads/ /app/static/uploads

EXPOSE 5000/tcp

ENTRYPOINT ["waitress-serve"] 
CMD ["--host", "0.0.0.0", "--port", "5000", "--threads", "8", "--call", "app:createApp"]
