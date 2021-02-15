# AWS Auto Scaling Fargate Cluster— Quickstart with CloudFormation

Running a cluster of machines can be hard. Fargate removes the need to manage instances on which to run containers. In this article, I demonstrate how to create a service running on Amazon’s Elastic Container Service with Fargate using CloudFormation.

Fargate removes the need to think about running a container on a machine and instead leaves the user to only need to think about running applications on the container level. A lot more knowledge and understanding is required to manage your own instances; check out our previous on [Auto Scaling with a SpotFleet Cluster](hhttps://t3chflicks.medium.com/aws-auto-scaling-spot-fleet-cluster-quickstart-with-cloudformation-6504a61f7aab) if you’re interested in learning more about this.

![Photo by [Sam Solomon](https://unsplash.com/@samsolomon?utm_source=medium&utm_medium=referral) on [Unsplash](https://unsplash.com?utm_source=medium&utm_medium=referral)](https://cdn-images-1.medium.com/max/6016/0*EGiTv_smBGt_KNJg)*

Photo by [Sam Solomon](https://unsplash.com/@samsolomon?utm_source=medium&utm_medium=referral) on [Unsplash](https://unsplash.com?utm_source=medium&utm_medium=referral)*

### Architecture

For this example, I am going to create a Dockerised Python web server and deploy it to an ECS cluster which auto scales the number of Fargate containers. An Application Load Balancer (ALB) will be used to create an API which load balances the containers running the service.

![](https://cdn-images-1.medium.com/max/2000/1*bgpOCiWGln5MOh9AoBqCTQ.png)

### The service

The service is an asynchronous Python web server running on port 5000 with CORS enabled. Note that the healthcheck endpoint is required for ECS to keep track of the service.

    from aiohttp import web
    import aiohttp_cors
    import json

    async def healthcheck(_):
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
        return web.Response(text=json.dumps("Healthy"), headers=headers, status=200)
    
    async def helloworld(_):
        return web.Response(text="<h1>HELLO WORLD</h1>", content_type='text/html', status=200)


    app = web.Application()
    cors = aiohttp_cors.setup(app)
    app.router.add_get("/healthcheck", healthcheck)
    app.router.add_get("/", helloworld)

    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
    })

    # Configure CORS on all routes.
    for route in list(app.router.routes()):
        cors.add(route)

    if __name__ == "__main__":
        print("Starting service")
        web.run_app(app, host="0.0.0.0", port=(5000))


### Deployment

Using AWS CLI to deploy CloudFormation is as simple as:

    `aws cloudformation create-stack --stack-name service --template-body file://template.yml --capabilities CAPABILITY_NAMED_IAM`

The deployment is split into four templates:

* VPC — [code](https://github.com/sk-t3ch/AWS-Auto-Scaling-Fargate-Cluster/blob/master/aws/00_vpc.yml)

* Load Balancer — [code](https://github.com/sk-t3ch/AWS-Auto-Scaling-Fargate-Cluster/blob/master/aws/01_load_balancer.yml)

* Cluster — [code](https://github.com/sk-t3ch/AWS-Auto-Scaling-Fargate-Cluster/blob/master/aws/02_cluster.yml)

* Service — [code](https://github.com/sk-t3ch/AWS-Auto-Scaling-Fargate-Cluster/blob/master/aws/03_service.yml)

## Let’s Build! 🔩

### VPC

I am building this service inside a VPC described in a previous article
[**Virtual Private Cloud on AWS — Quickstart with CloudFormation**
*A Virtual Private Cloud is the foundation from which to build a new system. In this article, I demonstrate how to…*medium.com](https://medium.com/swlh/virtual-private-cloud-on-aws-quickstart-with-cloudformation-4583109b2433)

It’s pretty standard. There are three public and three private (hybrid) subnets.

### Load Balancer

The service requires a public facing load balancer which distributes HTTP requests to the machines running the web server.

    LoadBalancerSecGroup:
        Type: AWS::EC2::SecurityGroup
        Properties:
            GroupDescription: Load balancer only allow http port traffic
            VpcId: !ImportValue VPCID
            SecurityGroupIngress:
            CidrIp: 0.0.0.0/0
            FromPort: 80
            IpProtocol: TCP
            ToPort: 80
    LoadBalancer:
        Type: AWS::ElasticLoadBalancingV2::LoadBalancer
        Properties:
            SecurityGroups:
            - !Ref LoadBalancerSecGroup
            Subnets:
            - !ImportValue PublicSubnetA
            - !ImportValue PublicSubnetB


### Cluster

The cluster orchestrates containers running on the machines. If you are unfamiliar with Docker, check out this [article](https://medium.com/@t3chflicks/home-devops-pipeline-a-junior-engineers-tale-1-4-336ed07a6ec0). Dockerising the Python web server can be done in few lines:

    FROM python:3.7-slim
    COPY requirements.txt /app/requirements.txt
    WORKDIR /app
    RUN pip install -r requirements.txt
    COPY src /app
    EXPOSE 5000
    CMD python app.py

In 2020, AWS introduced Capacity Providers to ECS, this includes Spot Fargate, which are a fraction of the price of standard Fargate containers.

The following template configures an ECS cluster using Fargate Spot, and ECR to store the Docker image of the Python web server:

    ECSCluster:
        Type: 'AWS::ECS::Cluster'
        Properties:
        ClusterName: ECSCluster
        CapacityProviders:
            - FARGATE_SPOT
        DefaultCapacityProviderStrategy:
            - CapacityProvider: FARGATE_SPOT
            Weight: 1
        ClusterSettings:
            - Name: containerInsights
            Value: enabled
    
    ECRRepository: 
        Type: AWS::ECR::Repository


### Service

I’ve configured the load balancer to listen on port 80 for HTTP requests and send them to a Target Group — a reference we can use when defining the service to access traffic.

    TargetGroup:
        Type: AWS::ElasticLoadBalancingV2::TargetGroup
        Properties:
        Port: 5000
        Protocol: HTTP
        VpcId: !ImportValue VPCID
        HealthCheckIntervalSeconds: 60
        HealthCheckTimeoutSeconds: 5
        UnhealthyThresholdCount: 5
        HealthCheckPath: /healthcheck
        TargetGroupAttributes:
            - Key: deregistration_delay.timeout_seconds
            Value: 2
            
    LoadBalancerListener:
        Type: AWS::ElasticLoadBalancingV2::Listener
        Properties:
        DefaultActions:
            - TargetGroupArn: !Ref TargetGroup
            Type: forward
        LoadBalancerArn: !ImportValue LoadBalancerArn
        Port: 80
        Protocol: HTTP
        
    ListenerRule:
        Type: AWS::ElasticLoadBalancingV2::ListenerRule
        Properties:
        Actions:
            - TargetGroupArn: !Ref TargetGroup
            Type: forward
        Conditions:
            - Field: path-pattern
            Values:
                - '*'
        ListenerArn: !Ref LoadBalancerListener
        Priority: 1

ECS runs the Task Definition as a persistent service using the web server image in ECR. It’s as simple as defining it as Fargate.

    TaskDefinition:
        Type: AWS::ECS::TaskDefinition
        Properties:
        Family: AppTaskDefinition
        TaskRoleArn: !GetAtt TaskRole.Arn
        NetworkMode: awsvpc
        ExecutionRoleArn: !Ref ExecutionRole
        RequiresCompatibilities:
            - FARGATE
        Memory: 0.5Gb
        Cpu: 256
        ContainerDefinitions:
            - Name: ServiceContainer
            PortMappings:
                - ContainerPort: 5000
            Essential: true
            Image: <your_image>
            LogConfiguration:
                LogDriver: awslogs
                Options:
                awslogs-group: !Ref LogGroup
                awslogs-region: !Ref 'AWS::Region'
                awslogs-stream-prefix: ecs

    Service:
        Type: AWS::ECS::Service
        DependsOn:
        - ListenerRule
        Properties:
        Cluster: !ImportValue ECSCluster
        LaunchType: FARGATE
        DesiredCount: 1
        LoadBalancers:
            - ContainerName: ServiceContainer
            ContainerPort: 5000
            TargetGroupArn: !Ref TargetGroup
        DeploymentConfiguration:
            MinimumHealthyPercent: 100
            MaximumPercent: 200
        HealthCheckGracePeriodSeconds: 30
        TaskDefinition: !Ref TaskDefinition
        NetworkConfiguration:
            AwsvpcConfiguration:
            AssignPublicIp: ENABLED
            Subnets:
                - !ImportValue PublicSubnetA
                - !ImportValue PublicSubnetB
            SecurityGroups:
                - !Ref ContainerSecurityGroup


Configuring an auto-scaling policy on the containers works in much the same way as the EC2 machines as they have defined memory and CPU so can be scaled based on those metrics, too:

    AutoScalingTarget:
        Type: AWS::ApplicationAutoScaling::ScalableTarget
        Properties:
        MaxCapacity: 3
        MinCapacity: 2
        ResourceId: !Join ["/", [service, !ImportValue ECSCluster, !GetAtt Service.Name]]
        RoleARN: !ImportValue ECSServiceAutoScalingRoleArn
        ScalableDimension: ecs:service:DesiredCount
        ServiceNamespace: ecs
        
    AutoScalingPolicy:
        Type: AWS::ApplicationAutoScaling::ScalingPolicy
        Properties:
        PolicyName: ServiceAutoScalingPolicy
        PolicyType: TargetTrackingScaling
        ScalingTargetId: !Ref AutoScalingTarget
        TargetTrackingScalingPolicyConfiguration:
            PredefinedMetricSpecification:
            PredefinedMetricType: ECSServiceAverageCPUUtilization
            ScaleInCooldown: 10
            ScaleOutCooldown: 10
            TargetValue: 70

## Usage

After a successful deployment, it is possible to access the DNS name of the ALB in the EC2 section of the AWS console which should look something like:

    loadb-LoadB-R7RVQD09YC9O-1401336014.eu-west-1.elb.amazonaws.com

I am now able to view the response inside Post Man:

![](https://cdn-images-1.medium.com/max/2000/1*jkALWUQcao3a5OO1ejPqwA.png)

### Use a Domain Name

    loadb-LoadB-R7RVQD09YC9O-1401336014.eu-west-1.elb.amazonaws.com

But it’s quite simple to use a custom domain using AWS. You must first transfer your DNS management to Route 53 and then create a new record set which is aliased to the load balancer.

### Thanks For Reading

I hope you have enjoyed this article. If you like the style, check out [T3chFlicks.org](https://t3chflicks.org/Projects/aws-quickstart-series) for more tech focused educational content ([YouTube](https://www.youtube.com/channel/UC0eSD-tdiJMI5GQTkMmZ-6w), [Instagram](https://www.instagram.com/t3chflicks/), [Facebook](https://www.facebook.com/t3chflicks), [Twitter](https://twitter.com/t3chflicks)).

Resources:

* [https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecs-taskdefinition.html](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecs-taskdefinition.html)