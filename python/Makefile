export DOCKER_USERNAME ?= salant
export DOCKER_HOSTNAME ?= github.ibm.com
export DOCKER_PASSWORD ?= XXXXXXXXXXXx
export DOCKER_NAMESPACE ?= salant
export DOCKER_TAGNAME ?= v1

export REPO_HOSTNAME ?= ghcr.io
export REPO_USERNAME ?= elsalant

DOCKER_IMG_NAME ?= smartmedia-module
CHART_IMG_NAME ?= smartmedia-chart
DOCKER_FILE ?= Dockerfile
DOCKER_CONTEXT ?= .
DOCKER_LOCATION ?= build
APP_IMG ?= ${REPO_HOSTNAME}/${REPO_USERNAME}/${DOCKER_IMG_NAME}:${DOCKER_TAGNAME}
CHART_IMG ?= ${REPO_HOSTNAME}/${REPO_USERNAME}/${CHART_IMG_NAME}:${HELM_TAGNAME}
CHART ?= ${DOCKER_IMG_NAME}

export HELM_TAGNAME ?= 0.0.1
export HELM_TOKEN ?= $(DOCKER_PASSWORD)
export HELM_USERNAME ?= elsalant
export HELM_HOSTNAME ?= ghcr.io
export HELM_INSTALL_NAME ?= smartmedia-module
export HELM_CHART_NAME ?= smartmedia-chart
export HELM_REPO ?= oci://ghcr.io/$(HELM_USERNAME)

export KIND_CLUSTER ?= sm-read

.PHONY: docker-all
docker-all: docker-build docker-push

.PHONY: docker-build
docker-build:
	docker build $(DOCKER_CONTEXT) -t ${APP_IMG} -f $(DOCKER_LOCATION)/$(DOCKER_FILE)

.PHONY: docker-push
docker-push:
	docker login --username ${DOCKER_USERNAME} --password ${DOCKER_PASSWORD} ghcr.io/elsalant
	docker push ${APP_IMG}

.PHONY: docker-rmi
docker-rmi:
	docker rmi ${APP_IMG} || true

.PHONY: push-to-kind
push-to-kind:
	kind load docker-image ${APP_IMG} --name $(KIND_CLUSTER)

CHART := ${DOCKER_HOSTNAME}/${DOCKER_IMG_NAME}
TEMP := /tmp

HELM_VALUES ?=

HELM_RELEASE ?= ${HELM_INSTALL_NAME}
TEMP := /tmp

export HELM_EXPERIMENTAL_OCI=1
export GODEBUG=x509ignoreCN=0

.PHONY: helm-login
helm-login:
	ifneq (${HELM_PASSWORD},)
		helm registry login -u "${HELM_USERNAME}" -p "${HELM_PASSWORD}" ${HELM_HOSTNAME}
	endif

.PHONY: helm-uninstall
helm-uninstall:
	helm uninstall ${HELM_RELEASE} || true

.PHONY: helm-package
helm-package:
	helm package $(CHART_IMG_NAME) -d $(TEMP)

.PHONY: helm-push
helm-push:
	helm push ${TEMP}/${HELM_CHART_NAME}-${HELM_TAGNAME}.tgz ${HELM_REPO}

.PHONY: helm-install
helm-install:
	helm install $(HELM_RELEASE) ${HELM_REPO}/${HELM_CHART_NAME}

