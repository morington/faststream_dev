NETWORK_NAME = xcvzv97opksje

all: build

_create_network:
	@echo "Создание сети Docker, если она не существует..."
	docker network inspect $(NETWORK_NAME) >/dev/null 2>&1 || docker network create $(NETWORK_NAME)

build:
	make _create_network
	@echo "Запуск..."
	docker compose up -d
	@echo "Успешно!"

down:
	@echo "Останавливаем..."
	docker compose down
	@echo "Успешно!"

restart:
	make down
	make
