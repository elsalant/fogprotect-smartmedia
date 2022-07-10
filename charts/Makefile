export HELM_TAGNAME ?= 0.0.1
export HELM_TOKEN ?= XXXXXXXXXXX
export HELM_USERNAME ?= elsalant
export HELM_HOSTNAME ?= ghcr.io
export HELM_INSTALL_NAME ?= smartmedia-module
export HELM_CHART_NAME ?= smartmedia-chart

export REPO_USERNAME ?= elsalant
export HELM_REPO ?= oci://ghcr.io/$(REPO_USERNAME)

CHART_IMG_NAME ?= smartmedia-module
CHART_IMG ?= ${REPO_HOSTNAME}/${REPO_USERNAME}/${CHART_IMG_NAME}-${HELM_TAGNAME}
CHART ?= ${CHART_IMG_NAME}

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

