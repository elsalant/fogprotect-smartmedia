# fogprotect-smartmedia
Repo for second half project work on the Smart Media use case for FogProtect

The use case determines based on a situationstatus value (set through a configmap) where to proxy an incoming REST request to.
Note:  The OPA policy is automatically loaded from the configmap by the deployment-opa file
       OPA is brought up automatically by the files in the templates directory
To run:
1. Install the configmaps in the yaml directory (moduleConfig.yaml, policy.yaml, and either safe-situation.yaml or unsafe-high-situation)
1. Install the yaml to externalize the ingress gateway: sm-smartmedia-ingress.yaml
1. helm install sm oci://ghcr.io/elsalant/smartmedia-chart

To test:
In script directory:
./runPortForward.sh
./runCurl.sh

