NAME := mask_det

REGISTRY := 10.110.63.67/iai

.PHONY: build_cpu build_gpu start_cpu start_gpu stop_cpu stop_gpu push_cpu push_gpu clean_data

#DATE := `date +%y.%m.%d`

#VERSION=v0.1.$(DATE)

VERSION=v1.0

# 构建镜像
build_cpu:
	docker build --rm -f Dockerfile_cpu -t $(REGISTRY)/$(NAME):$(VERSION)-cpu .

build_gpu:
	docker build --rm -f Dockerfile_gpu -t $(REGISTRY)/$(NAME):$(VERSION)-gpu .

# 启动容器
start_cpu:
	docker-compose -f docker-compose/cpu/docker-compose.yml up -d

start_gpu:
	docker-compose -f docker-compose/gpu/docker-compose.yml up -d

# 停止并删除容器
stop_cpu:
	docker-compose -f docker-compose/cpu/docker-compose.yml down

stop_gpu:
	docker-compose -f docker-compose/gpu/docker-compose.yml down

# 推送镜像到存储
push_cpu:
	docker push $(REGISTRY)/$(NAME):$(VERSION)-cpu

push_gpu:
	docker push $(REGISTRY)/$(NAME):$(VERSION)-gpu

clean_data:
	rm -rf logs/*

