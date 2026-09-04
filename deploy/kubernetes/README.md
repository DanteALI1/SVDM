# Kubernetes deployment for SVDB
#
# Prerequisites: cluster with ingress controller, storage class, secrets.
#
# Quick start:
#   kubectl apply -f namespace.yaml
#   kubectl apply -f secret.yaml   # edit first
#   kubectl apply -f postgres.yaml
#   kubectl apply -f redis.yaml
#   kubectl apply -f backend.yaml
#   kubectl apply -f frontend.yaml
#   kubectl apply -f ingress.yaml
#
# Images: build & push your registry images for backend/frontend,
# then update image: fields below.
