output "ssh_login" {
    value = "ssh -i ${var.private_key} ${var.user}@${aws_instance.app_server.public_dns}"
}