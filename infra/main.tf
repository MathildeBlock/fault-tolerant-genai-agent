terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {}

  # AzureRM v4 needs this for plan/apply; null allows ARM_SUBSCRIPTION_ID.
  subscription_id = var.subscription_id
}

resource "random_string" "app_suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_resource_group" "api" {
  name     = var.resource_group_name
  location = var.location
}

resource "azurerm_service_plan" "api" {
  name                = "${var.app_name}-${random_string.app_suffix.result}-plan"
  resource_group_name = azurerm_resource_group.api.name
  location            = azurerm_resource_group.api.location
  os_type             = "Linux"
  sku_name            = var.service_plan_sku
}

resource "azurerm_linux_web_app" "api" {
  name                = "${var.app_name}-${random_string.app_suffix.result}"
  resource_group_name = azurerm_resource_group.api.name
  location            = azurerm_service_plan.api.location
  service_plan_id     = azurerm_service_plan.api.id
  https_only          = true

  site_config {
    application_stack {
      docker_image_name = var.container_image
    }
  }

  app_settings = {
    WEBSITES_PORT = tostring(var.container_port)
  }
}