# Foresitecore

## Setup Project

### Clone the project

Clone the project from Github.

```sh
git clone https://github.com/matariyashantilal/Foresitecore.git
cd Foresitecore/
```

### Build the images and run the server from docker containers

```sh
docker-compose up -d --build
```

### Check the logs of the docker container or server

```sh
docker-compose logs -f --tail 10 web
```