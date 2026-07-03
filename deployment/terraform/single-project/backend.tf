terraform {
  backend "gcs" {
    bucket = "shogoorg-samples-rest-terraform-state"
    prefix = "samples-rest/dev"
  }
}
