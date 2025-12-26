variable "ssh_key_name" {
  type = string
  nullable = false
}

variable "absolute_path_to_ssh_key" {
  type = string
  nullable = false
  validation {
    condition     = fileexists(var.config_path)
    error_message = "The file specified by config_path does not exist."
  }
  validation {
    condition     = endswith(var.ssh_public_key_path, ".pub")
    error_message = "ssh_public_key_path must end with .pub."
  }
}
