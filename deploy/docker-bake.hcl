variable "REGISTRY" {
  default = "ghcr.io/task-studio"
}

variable "TAG" {
  default = "latest"
}

group "default" {
  targets = [
    "auth",
    "studio-api",
    "catalog",
    "sessions",
    "grading",
    "integrations",
    "tutor",
    "search",
    "analytics",
    "media",
    "lab-runner",
    "orchestrator",
    "web",
    "pack-studio",
  ]
}

target "_common" {
  context = ".."
  platforms = ["linux/amd64", "linux/arm64"]
}

target "auth" {
  inherits = ["_common"]
  dockerfile = "services/auth/Dockerfile"
  tags = ["${REGISTRY}/task-studio-auth:${TAG}"]
}

target "studio-api" {
  inherits = ["_common"]
  dockerfile = "services/studio-api/Dockerfile"
  tags = ["${REGISTRY}/task-studio-studio-api:${TAG}"]
}

target "catalog" {
  inherits = ["_common"]
  dockerfile = "services/catalog/Dockerfile"
  tags = ["${REGISTRY}/task-studio-catalog:${TAG}"]
}

target "sessions" {
  inherits = ["_common"]
  dockerfile = "services/sessions/Dockerfile"
  tags = ["${REGISTRY}/task-studio-sessions:${TAG}"]
}

target "grading" {
  inherits = ["_common"]
  dockerfile = "services/grading/Dockerfile"
  tags = ["${REGISTRY}/task-studio-grading:${TAG}"]
}

target "integrations" {
  inherits = ["_common"]
  dockerfile = "services/integrations/Dockerfile"
  tags = ["${REGISTRY}/task-studio-integrations:${TAG}"]
}

target "tutor" {
  inherits = ["_common"]
  dockerfile = "services/tutor/Dockerfile"
  tags = ["${REGISTRY}/task-studio-tutor:${TAG}"]
}

target "search" {
  inherits = ["_common"]
  dockerfile = "services/search/Dockerfile"
  tags = ["${REGISTRY}/task-studio-search:${TAG}"]
}

target "analytics" {
  inherits = ["_common"]
  dockerfile = "services/analytics/Dockerfile"
  tags = ["${REGISTRY}/task-studio-analytics:${TAG}"]
}

target "media" {
  inherits = ["_common"]
  dockerfile = "services/media/Dockerfile"
  tags = ["${REGISTRY}/task-studio-media:${TAG}"]
}

target "lab-runner" {
  inherits = ["_common"]
  dockerfile = "services/lab-runner/Dockerfile"
  tags = ["${REGISTRY}/task-studio-lab-runner:${TAG}"]
}

target "orchestrator" {
  inherits = ["_common"]
  dockerfile = "services/orchestrator/Dockerfile"
  tags = ["${REGISTRY}/task-studio-orchestrator:${TAG}"]
}

target "web" {
  context = "../apps/web"
  dockerfile = "Dockerfile"
  platforms = ["linux/amd64", "linux/arm64"]
  tags = ["${REGISTRY}/task-studio-web:${TAG}"]
}

target "pack-studio" {
  context = "../apps/pack-studio"
  dockerfile = "Dockerfile"
  platforms = ["linux/amd64", "linux/arm64"]
  tags = ["${REGISTRY}/task-studio-pack-studio:${TAG}"]
}
