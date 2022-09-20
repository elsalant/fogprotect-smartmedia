#!/bin/bash
# Create a kind cluster with a shorter interval for checking refresh of configmap values
echo "Enter new cluster name"
read clusterName
echo kind create cluster --name $clusterName --config=demo-cluster.yaml
