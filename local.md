# Navodila za local development
### Windows
Na Docker desktop greš pod settings -> Kubernetes -> Enable Kubernetes -> kind

Potem Powershell kot admin in vpišeš:
```
winget install Kubernetes.kind
```
Zapreš terminal in ga ponovno odpreš.
```
kind create cluster --name dev-clusterž
```
Greš v mapo od mikrostoritve (primer za users (./sistem-za-obvescanje/services/users))
```
docker build -t users:local .
kind load docker-image users:local --name dev-cluster
kubectl apply -f k8s/
kubectl get pods, svc -o wide
```
Če ti kaže da je running in 1/1 potem je vse ok.
Za lokalni dostop do servisa:
```
kubectl port-forward svc/users-service 8000:80
```


### Za helm chart
```
winget install Helm.Helm
```