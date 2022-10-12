# fogprotect-smartmedia
Repo for second half project work on the Smart Media use case for FogProtect

The use case determines based on a situationstatus value (set through a configmap) where to proxy an incoming REST request to.
Note:  The OPA policy is automatically loaded from the configmap by the deployment-opa file
       OPA is brought up automatically by the files in the templates directory
To run:
1. Install the configmaps in the yaml directory (moduleConfig.yaml and either safe-situation.yaml or unsafe-high-situation)
1a. Install the policies: yaml/policy_smartmedia.yaml
2. Install the yaml to externalize the ingress gateway: sm-smartmedia-ingress.yaml
3. helm install sm oci://ghcr.io/elsalant/smartmedia-chart
4. kubectl get pods - get pod for opa then forward, e.g. 
   kubectl port-forward opa-75b6c4cd69-clv62 8181

NOTE:
policies are installed from configmap, policy-smartmedia in yaml/policy_smartmedia.yaml
=======
2. Load policy configmap: yaml/policy_smartmedia.yaml
3. Install the yaml to externalize the ingress gateway: sm-smartmedia-ingress.yaml
4. helm install sm oci://ghcr.io/elsalant/smartmedia-chart
5. kubectl get pods - get pod for opa then forward, e.g. 
   kubectl port-forward opa-75b6c4cd69-clv62 8181

NOTE: Policies are installed from configmap!!
To test:
In script directory:
./runPortForward.sh
./runCurl.sh

