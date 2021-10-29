pipeline {
    agent any
    stages {
        stage("Docker Build Image") {
            steps {
                sh "docker build -f Dockerfile-cardfillingbot -t nkuznetsov44/cardfillingbot:${ENVIRONMENT} ."
            }
        }
        stage("Docker Push Image") {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASSWORD')]) {
                    sh "docker login -u ${DOCKER_USER} -p ${DOCKER_PASSWORD}"
                }
                sh "docker push nkuznetsov44/cardfillingbot:${ENVIRONMENT}"
            }
        }
        stage("Docker Run Container") {
            sh "chmod +x startup-cardfillingbot.sh"
            if (params.ENVIRONMENT == "prod") {
                environment {
                    PORT = "8888"
                }
                withCredentials([
                    usernamePassword(credentialsId: 'cardfillingbot-mysqldb-prod', usernameVariable: 'MYSQL_USER', passwordVariable: 'MYSQL_PASSWORD'),
                    string(credentialsId: 'mysqldb-host-prod', variable: 'MYSQL_HOST'),
                    string(credentialsId: 'cardfillingbot-mysqldb-database-prod', variable: 'MYSQL_DATABASE'),
                    string(credentialsId: 'cardfillingbot-webhook-url-prod', variable: 'WEBHOOK_URL'),
                    string(credentialsId: 'cardfillingbot-telegram-token-prod', variable: 'TELEGRAM_TOKEN')
                ]) {
                    sh "./startup-cardfillingbot.sh"
                }
            }
            else {
                environment {
                    PORT = "8889"
                }
                withCredentials([
                    usernamePassword(credentialsId: 'cardfillingbot-mysqldb-develop', usernameVariable: 'MYSQL_USER', passwordVariable: 'MYSQL_PASSWORD'),
                    string(credentialsId: 'mysqldb-host-develop', variable: 'MYSQL_HOST'),
                    string(credentialsId: 'cardfillingbot-mysqldb-database-develop', variable: 'MYSQL_DATABASE'),
                    string(credentialsId: 'cardfillingbot-webhook-url-develop', variable: 'WEBHOOK_URL'),
                    string(credentialsId: 'cardfillingbot-telegram-token-develop', variable: 'TELEGRAM_TOKEN')
                ]) {
                    sh "./startup-cardfillingbot.sh"
                }
            }
        }
    }
}