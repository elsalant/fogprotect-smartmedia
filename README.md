# fogprotect-smartmedia
Repo for second half project work on the Smart Media use case for FogProtect

The use case determines based on a situationstatus value (set through a configmap) where to proxy an incoming REST request to.
To run:
1. Start OPA server. (Filtering not done though in the code)
1. Install the configmaps in the yaml directory
1. helm install smartmedia 
