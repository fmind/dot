# Docs: https://opentofu.org/docs/language/values/variables/
variable "project" {
  description = "GCP project ID that owns every resource in this configuration"
  type        = string
}

variable "region" {
  description = "Default GCP region for regional resources"
  type        = string
  default     = "europe-west1"

  validation {
    condition     = can(regex("^[a-z]+-[a-z]+[0-9]+$", var.region))
    error_message = "Region must have the GCP region-name shape (e.g. europe-west1 or europe-west12); verify service availability separately."
  }
}

variable "labels" {
  description = "Common labels stamped on every resource for cost attribution"
  type        = map(string)
  default     = {}
}
