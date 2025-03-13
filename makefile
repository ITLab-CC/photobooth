.PHONY: run run-dev stop clean help

help: check-not-root
	@echo "Usage: make [option]"
	@echo ""
	@echo "Options:"
	@echo "  run              Run all services in docker"
	@echo "  run-dev          Run all services for development"
	@echo "  stop             Stop all services"
	@echo "  clean			  Remove all generated files, including .env, logs, data, and .venv"
	@echo "  help             Show this help message"

check-not-root:
	@if [ "$$(id -u)" = "0" ]; then \
	  echo "Error: Do not run this Makefile as root (UID 0)."; \
	  exit 1; \
	fi
	@if [ -n "$${SUDO_USER}" ]; then \
	  echo "Error: Do not run this Makefile via sudo."; \
	  exit 1; \
	fi


check-docker-rights:
	@if [ $$(id -nG | grep -cw docker) -eq 0 ]; then \
		tput clear > /dev/tty; \
		tput cup 0 0 > /dev/tty; \
		tput ed > /dev/tty; \
		echo "\e[1;31m========================= ATTENTION REQUIRED =========================\e[0m" > /dev/tty; \
		echo "\e[1;33mThis user is not in the docker group.\e[0m" > /dev/tty; \
		echo "\e[1;33mPlease follow the steps below:\e[0m" > /dev/tty; \
		echo "\e[1;32m1. Run: \e[1;34msudo usermod -aG docker $$USER\e[0m" > /dev/tty; \
		echo "\e[1;32m2. Reopen your current session.\e[0m" > /dev/tty; \
		echo "\e[1;34m   (If you are using VS Code, restart VS Code)\e[0m" > /dev/tty; \
		echo "\e[1;32m3. Rerun the makefile.\e[0m" > /dev/tty; \
		echo "\e[1;31m======================================================================\e[0m" > /dev/tty; \
		exit 1; \
	fi

install: check-not-root
	@chmod +x setup.sh
	@./setup.sh --check || sudo ./setup.sh
	@echo "All dependencies are installed"

build: check-not-root
	@if [ ! -d "frontend/dist" ]; then \
		cd frontend; \
		npm install; \
		npm run build; \
		cd ..; \
	fi

	@if [ ! -d ".venv" ]; then \
		python3 -m venv .venv; \
		bash -c "source .venv/bin/activate && pip install -r requirements.txt && deactivate"; \
	fi

generate-env-files: check-not-root
	@if [ ! -f .env ]; then \
		echo "Generating .env file..."; \
		bash -c "source .venv/bin/activate && python3 setup.py --create-env"; \
	fi

DATA_EXISTS=$(shell test -d data && echo yes || echo no)
CURRENT_FOLDER=$(shell pwd)
run: check-not-root install build generate-env-files check-docker-rights stop
	@docker compose -f docker-compose.yml up -d --build

	@screen -dmS mongodb bash -c "docker logs -f mongodb 2>&1 | tee logs/mongodb.log"
	@screen -dmS redis bash -c "docker logs -f redis 2>&1 | tee logs/redis.log"
	@if [ "$(DATA_EXISTS)" = "no" ]; then \
		echo "Running setup script..."; \
		docker build -t my-python-setup -f dockerfile-setup . && \
		docker run --rm -v "$(CURRENT_FOLDER)/.env:/app/.env" --network photo_booth_network my-python-setup; \
	fi
	@screen -dmS backend bash -c "docker logs -f backend 2>&1 | tee logs/backend.log"

	@echo "------------------------------------------------------"
	@echo "All services are running in the background."
	@echo "The logs are available in the logs/ directory."
	@echo "------------------------------------------------------"

run-dev: check-not-root install build generate-env-files check-docker-rights stop
	@docker compose -f docker-compose-dev.yml up --no-start

	@screen -dmS mongodb bash -c "docker compose -f docker-compose-dev.yml up mongodb 2>&1 | tee logs/mongodb.log"
	@screen -dmS redis bash -c "docker compose -f docker-compose-dev.yml up redis 2>&1 | tee logs/redis.log"
	@if [ "$(DATA_EXISTS)" = "no" ]; then \
		echo "Running setup script..."; \
		bash -c "source .venv/bin/activate && set -a && source .env-dev && set +a && python3 setup.py --setup --skip-env"; \
	fi
	@screen -dmS backend bash -c "source .venv/bin/activate && set -a && source .env-dev && set +a && python3 main.py 2>&1 | tee logs/backend.log"

	@echo "------------------------------------------------------"
	@echo "All services are running in the background."
	@echo "The logs are available in the logs/ directory."
	@echo "------------------------------------------------------"

stop: check-not-root check-docker-rights stop-dev
	@docker compose down

stop-dev: check-not-root check-docker-rights
	@for service in backend mongodb redis; do \
		screen -ls | grep ".$$service" | awk '{print $$1}' | while read session; do \
			echo "Stopping screen session $$session..."; \
			screen -S $$session -X quit; \
		done; \
	done
	@docker compose -f docker-compose-dev.yml down

clean: stop
	@if [ -d "logs" ]; then \
		rm -rf logs/*.log; \
	fi
	@if [ -d "data" ]; then \
		sudo rm -rf data; \
	fi
	@if [ -f ".env" ]; then \
		rm .env; \
	fi
	@if [ -f ".env-dev" ]; then \
		rm .env-dev; \
	fi
	@if [ -f "print-service/.env" ]; then \
		rm print-service/.env; \
	fi
	@if [ -d ".venv" ]; then \
		rm -rf .venv; \
	fi
	@if [ -d "frontend/dist" ]; then \
		rm -rf frontend/dist; \
	fi
