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

  validation {
    condition = (
      length(var.app_name) >= 2 &&
      length(var.app_name) <= 47 &&
      can(regex("^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", var.app_name))
    )
    error_message = "app_name must be 2-47 lowercase letters, numbers, or hyphens, and start and end with a letter or number."
  }
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

  validation {
    condition     = var.container_port >= 1 && var.container_port <= 65535 && floor(var.container_port) == var.container_port
    error_message = "container_port must be an integer between 1 and 65535."
  }
}