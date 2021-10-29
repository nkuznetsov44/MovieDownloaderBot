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
    }
}