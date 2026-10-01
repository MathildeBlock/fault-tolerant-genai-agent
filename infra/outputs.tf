output "api_url" {
  description = "HTTPS URL of the deployed API."
  value       = "https://${azurerm_linux_web_app.api.default_hostname}"
}

output "resource_group_name" {
  description = "Resource group containing the API resources."
  value       = azurerm_resource_group.api.name
}