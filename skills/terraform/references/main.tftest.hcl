# Docs: https://opentofu.org/docs/cli/commands/test/
# Mock the provider so plan-only tests never configure a real cloud client.
mock_provider "google" {}

variables {
  project = "test-project"
  region  = "europe-west1"
}

run "multi_digit_region" {
  command = plan

  variables {
    region = "europe-west12"
  }

  assert {
    condition     = google_storage_bucket.assets.location == "europe-west12"
    error_message = "Region validation must accept multi-digit region numbers."
  }
}

run "reject_zone_as_region" {
  command = plan

  variables {
    region = "europe-west1-b"
  }

  expect_failures = [var.region]
}

run "bucket_is_locked_down" {
  command = plan

  assert {
    condition     = google_storage_bucket.assets.uniform_bucket_level_access == true
    error_message = "Assets bucket must enforce uniform bucket-level access."
  }

  assert {
    condition     = google_storage_bucket.assets.public_access_prevention == "enforced"
    error_message = "Assets bucket must block public access."
  }
}
