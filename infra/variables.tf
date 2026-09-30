variable "subscription_id" {
  description = "Azure subscription ID. Can also be supplied with ARM_SUBSCRIPTION_ID."
  type        = string
  default     = null
  nullable    = true
}

variable "location" {
  description = "Azure region for the API resources."
  type        = string
  default     = "westeurope"
}

variable "resource_group_name" {
  description = "Name of the resource group for the API."
  type        = string
  default     = "rg-fault-tolerant-genai-agent"
}

variable "app_name" {
  description = "Prefix for the globally unique Azure Web App name."
  type        = string
  default     = "fault-tolerant-genai-api"
}

variable "service_plan_sku" {
  description = "App Service plan SKU."
  type        = string
  default     = "B1"
}

variable "container_image" {
  description = "Container image containing the FastAPI application."
  type        = string
  default     = "nginx:latest"
}

variable "container_port" {
  description = "Port exposed by the container."
  type        = number
  default     = 80
}