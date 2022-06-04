terraform {
    required_providers {
        aws = {
            source  = "hashicorp/aws"
            version = "~> 3.27"
        }
    }

    required_version = ">= 0.14.9"
}

provider "aws" {
    profile = "default"
    region  = "us-east-1"
}

resource "aws_instance" "app_server" {
    ami           = var.ami
    instance_type = var.instance_type
    vpc_security_group_ids = [var.security_group]
    # subnet_id = var.subnet
    iam_instance_profile = var.instance_profile

    key_name = var.public_key

    connection {
        host      = self.public_ip
        user      = var.user
        file      = file(var.private_key)
    }

    tags = {
        Name = "van-app"
    }

    user_data = <<EOF
#!/bin/bash
yum update -y
yum install docker -y
service docker start
docker pull public.ecr.aws/s9q5i4m7/van_scrape_server
docker run -p 8501:8501 public.ecr.aws/s9q5i4m7/van_scrape_server
EOF

}