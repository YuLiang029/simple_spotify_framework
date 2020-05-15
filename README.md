# Simple spotify framework
This repository is a flask web application for simple spotify framework

## Local Installation (Two approaches)
1. 	Pycharm -> install requirements.txt
2.	Dockerfile installation

### Dockerfile installation
```
docker-compose build
docker-compose up
```

##	Heroku Deployment
```
heroku container:login
heroku create
heroku container:push web
heroku container:release web
heroku open
```
Details: [Container Registry & Runtime (Docker Deploys)](https://devcenter.heroku.com/articles/container-registry-and-runtime)

### Reset Heroku database
```
heroku pg:reset DATABASE_URL --app <app-name>
heroku pg:push <database name> DATABASE_URL --app <app-name>
```