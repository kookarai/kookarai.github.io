#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

# Function to update the code using git
update_code() {
  echo "Updating code using git..."
  git pull
}

# Function to set up nginx
setup_nginx() {
  echo "Setting up nginx..."
  sudo cp -rf ./default /etc/nginx/sites-available/default
  sudo service nginx restart
}

# Function to build and deploy services
build_and_deploy() {
  local service="$1"

  if [ "$service" == "all" ]; then
    echo "Building and deploying all services..."
    docker compose build
    docker compose up -d
  else
    echo "Building and deploying service: $service..."
    docker compose build "$service"
    docker compose stop "$service"
    docker compose rm -f "$service"
    docker compose up -d "$service"
  fi

  echo "Cleaning up unused Docker resources..."
  docker system prune -f -a --volumes
}

# Function to shut down services
shut_down() {
  local service="$1"

  if [ "$service" == "all" ]; then
    echo "Shutting down all services..."
    docker compose down
  else
    echo "Stopping service: $service..."
    docker compose stop "$service"
    docker compose rm -f "$service"
  fi

  echo "Cleaning up unused Docker resources..."
  docker system prune -f -a --volumes
}

# Main script logic
main() {
  update_code

  case "$1" in
    nginx)
      setup_nginx
      ;;
    build)
      if [ -z "$2" ]; then
        echo "Error: Please specify a service or 'all' to build."
        exit 1
      fi
      build_and_deploy "$2"
      ;;
    down)
      if [ -z "$2" ]; then
        echo "Error: Please specify a service or 'all' to shut down."
        exit 1
      fi
      shut_down "$2"
      ;;
    *)
      echo "Usage: $0 {nginx|build|down} [service_name|all]"
      exit 1
      ;;
  esac
}

main "$@"