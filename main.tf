terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "cal-sync-481621"
}

provider "google" {
  project = var.project_id
}

# Enable Google Calendar API
resource "google_project_service" "calendar_api" {
  service            = "calendar-json.googleapis.com"
  disable_on_destroy = false
}

# Output instructions for manual OAuth setup
output "setup_instructions" {
  value = <<-EOT

  ========================================
  NEXT STEPS - Manual OAuth Setup Required
  ========================================

  Terraform has enabled the Calendar API. Now create OAuth credentials:

  1. Open: https://console.cloud.google.com/apis/credentials?project=${var.project_id}

  2. Click "Configure Consent Screen":
     - User Type: External
     - App name: Calendar Sync
     - Support email: christian@livelyapps.com
     - Scopes: Add calendar scope (https://www.googleapis.com/auth/calendar)
     - Test users: Add christian@livelyapps.com and koch.chris@gmail.com
     - Save

  3. Click "Create Credentials" → "OAuth client ID":
     - Application type: Desktop app
     - Name: calendar-sync-client
     - Click "Create"

  4. Download the JSON file and save as both:
     - creds/source/credentials.json
     - creds/dest/credentials.json

  5. Run: python auth.py

  ========================================
  EOT
}
