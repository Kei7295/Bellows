.PHONY: help install run dev-core dev-web build check lint fmt test docker-build docker-up docker-down clean

help:
	@echo "Bellows v0.0.1 BETA"
	@echo "  make install      安装前端与 Python 开发依赖"
	@echo "  make run          构建前端并启动内核（http://127.0.0.1:7801）"
	@echo "  make dev-core     仅启动内核"
	@echo "  make dev-web      启动 Vite 开发服务器"
	@echo "  make build        构建前端"
	@echo "  make check        运行全部检查（lint + fmt-check + test + type-check + build）"
	@echo "  make lint         ruff check"
	@echo "  make fmt          ruff format"
	@echo "  make test         pytest"
	@echo "  make docker-build 构建镜像"
	@echo "  make docker-up/docker-down  Compose 启停"
	@echo "  make clean        清理构建与运行时产物（保留 data/）"

install:
	cd apps/web && npm ci --no-audit --no-fund
	cd apps/core && python3 -m pip install -r requirements-dev.txt

run:
	bash scripts/run.sh

dev-core:
	cd apps/core && python3 -m bellows_core --data-dir ../../data --port 7801

dev-web:
	cd apps/web && npm run dev

build:
	cd apps/web && npm run build

check:
	bash scripts/check.sh

lint:
	ruff check apps/core tests

fmt:
	ruff format apps/core tests

test:
	python3 -m pytest tests -q

docker-build:
	docker build -t bellows:0.0.1-beta .

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

clean:
	rm -rf apps/web/dist .pytest_cache .ruff_cache
	find apps/core -name '__pycache__' -type d -prune -exec rm -rf {} +
