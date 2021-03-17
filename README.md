# animl-email-relay
Lambda service for extracting images from wireless camera trap emails

## Related repos

- Animl Ingest            http://github.com/tnc-ca-geo/animl-ingest
- Animl API               http://github.com/tnc-ca-geo/animl-api
- Animl frontend          http://github.com/tnc-ca-geo/animl-frontend
- Animl base program      http://github.com/tnc-ca-geo/animl-base
- Animl ingest function   http://github.com/tnc-ca-geo/animl-ingest
- Animl ML resources      http://github.com/tnc-ca-geo/animl-ml
- Animl desktop app       https://github.com/tnc-ca-geo/animl-desktop

## About
animl-email-relay is a lambda function that is triggerd when an email is 
copied into an s3 bucket by AWS [Simple Email Service](https://docs.aws.amazon.com/ses/index.html). 
To set up email recieving on SES, follow the instructions [here](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/receiving-email-setting-up.html).

Currently, the handler supports emails coming from the following camera makers:
- [UOVision](http://www.uovision.com/)

## Setup

### Prerequisits
The instructions below assume you have the following tools globally installed:
- Serverless
- aws-cli

### Create "animl" AWS config profile
Good instructions 
[here](https://www.serverless.com/framework/docs/providers/aws/guide/credentials/).

### Make a project direcory and clone this repo
```
mkdir animl-email-relay
cd animl-email-relay
git clone https://github.com/tnc-ca-geo/animl-email-relay.git
cd animl-email-relay
```

### Create a .env file in the project's root directory with the following variables:
```
REGION=us-west-2  # AWS only supports email receiving in a few regions
AWS_PROFILE=animl
AWS_ACCOUNT_ID=[your-account-id]
```
*Note: AWS SES only supports email receiving in a [few regions](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/regions.html#region-receive-email).*

## Deployment
From project root folder (where ```serverless.yml``` lives), run the following to deploy or update the stack: 

```
# Deploy or update a development stack:
serverless deploy --stage dev

# Deploy or update a production stack:
serverless deploy --stage prod
```