kubectl  create configmap policy-smartmedia --from-file=/home/wp4/fogprotect-smartmedia/misc/policy_smartmedia.rego
kubectl label configmap policy-smartmedia openpolicyagent.org/policy=rego
while [[ $(kubectl get cm policy-smartmedia  -o 'jsonpath={.metadata.annotations.openpolicyagent\.org/policy-status}') != '{"status":"ok"}' 
]]; do echo "waiting for policy to be applied" && sleep 5; done
