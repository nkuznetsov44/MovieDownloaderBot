docker ps -aqf "name=cardfillingbot-${ENVIRONMENT}" | grep -q . && docker rm -fv cardfillingbot-${ENVIRONMENT}
docker run -d -p ${HOST_EXPOSED_PORT}:8000 --restart=unless-stopped --name=cardfillingbot-${ENVIRONMENT} \
    -e "TELEGRAM_TOKEN=${TELEGRAM_TOKEN}" \
    -e "MYSQL_USER=${MYSQL_USER}" \
    -e "MYSQL_PASSWORD=${MYSQL_PASSWORD}" \
    -e "MYSQL_HOST=${MYSQL_HOST}" \
    -e "MYSQL_DATABASE=${MYSQL_DATABASE}" \
    -e "WEBHOOK_URL=${WEBHOOK_URL}" \
    nkuznetsov44/cardfillingbot:${ENVIRONMENT}