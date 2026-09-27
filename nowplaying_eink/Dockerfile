ARG BUILD_FROM
FROM $BUILD_FROM

# tzdata: so the footer clock and quiet hours follow HA's TZ
RUN apk add --no-cache tzdata

WORKDIR /opt/nowplaying
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY app ./app
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
