# Example Service with AWS Auto Scaling Spot Fleet Cluster

Example of running an auto scaling Python web server using CloudFormation
* The blog post can be found [here](https://t3chflicks.medium.com/aws-auto-scaling-fargate-cluster-quickstart-with-cloudformation-dab2f84ffabd).

![architecture](./architecture.png)
![example usage](./example_usage.png)

# Step By Step Deployment
1. Deploy VPC
    * `aws cloudformation create-stack --stack-name vpc --template-body file://aws/00_vpc.yml --capabilities CAPABILITY_NAMED_IAM`
    * tutorial for VPC can be found [here](insert_medium_link)
1. Deploy Load Balancer
    * `aws cloudformation create-stack --stack-name loadbalancer --template-body file://aws/01_load_balancer.yml --capabilities CAPABILITY_NAMED_IAM`
1. Deploy Cluster
    * `aws cloudformation create-stack --stack-name cluster --template-body file://aws/02_ecs.yml --capabilities CAPABILITY_NAMED_IAM`
    * Upload Docker image of Web Sever to ECR 
      1. `docker build -t your_repo_name .`
      1. `docker tag your_repo_name your_repo_name_tag`
      1. `docker push your_repo_name`
1. Deploy Service
    * Update template with your Docker image
    * `aws cloudformation create-stack --stack-name service --template-body file://aws/03_service.yml --capabilities CAPABILITY_NAMED_IAM`

# Gotchas
* Login to AWS ECR `aws ecr get-login --registry-ids your_registry_id` and use this response for Docker login.
