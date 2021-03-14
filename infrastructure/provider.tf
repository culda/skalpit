provider "azurerm" {
  version = "=2.36.0"
  features {
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}