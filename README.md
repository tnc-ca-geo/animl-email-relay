# animl-email-relay

Lambda service for extracting images from wireless camera trap emails

## About

animl-email-relay is a lambda function that is triggered when an email is
copied into an s3 bucket by AWS [Simple Email Service](https://docs.aws.amazon.com/ses/index.html).
To set up email receiving on SES, follow the instructions [here](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/receiving-email-setting-up.html).

Currently, the handler supports emails coming from the following camera makers:

- [RidgeTec Lookout 4G LTE](https://www.trailcampro.com/products/ridgetec-lookout-4g-lte)
- [Cuddeback Cuddelink Cell](https://www.cuddeback.com/cuddelink)
- [Spartan GoLive 4G LTE](https://go.spartancamera.com/products/spartan-golive-4g-lte)

## Setup

### Prerequisits

The instructions below assume you have the following tools globally installed:

- Serverless
- Docker
- aws-cli

### Create "animl" AWS config profile

The name of the profile must be "animl", because that's what
`serverles.yml` will be looking for. Good instructions
[here](https://www.serverless.com/framework/docs/providers/aws/guide/credentials/).

_Note: AWS SES only supports email receiving in a [few regions](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/regions.html#region-receive-email)._

### Make a project direcory and clone this repo

```
mkdir animl-email-relay
cd animl-email-relay
git clone https://github.com/tnc-ca-geo/animl-email-relay.git
cd animl-email-relay
```

### Clone serverless-python-requirements plugin

This project runs in a Python Lambda environment, which means that all Python
dependencies must be installed in the OS in which the will be ultimately
executed. To accomplish this we use a Serverless plugin called
[serverless-python-requirements](https://www.serverless.com/plugins/serverless-python-requirements)
that, on `serverless deploy`, spins up a Docker container to mimic the AWS
Lambda Linux OS, downloads any Python requirements defined in
`requirements.txt` within the container, and packages them up to be added
to our Lambda deployment package.

The plugin works well for installing Python packages, but we also need to
include a Perl executable ([exiftool](https://exiftool.org/)) and its
dependencies in the final deployment package, and the
serverless-python-requirements plugin doesn't support some functionalty that
we need to make that happen out of the box (see issue
[here](https://github.com/UnitedIncome/serverless-python-requirements/issues/542)).
I created a fix and [pull request](https://github.com/UnitedIncome/serverless-python-requirements/pull/544)
to support this, but until the PR is accepted we have to clone the repo into
our project manually from my github profile. So from within the project root
directory, execute the following:

```
mkdir .serverless_plugins
cd .serverless_plugins
git clone --single-branch --branch recursive-docker-extra-files https://github.com/nathanielrindlaub/serverless-python-requirements.git
cd serverless-python-requirements
npm install
```

## Adding new Python packages

Perform the following steps if you need to use new Python packages in the
Lambda function.

### Create venv and activate it

In the parent directory of this project (one directory above root), run the following:

```
virtualenv venv --python=python3
source venv/bin/activate
```

### Add dependencies

```
# Example package installs
pip install requests
pip install PyExifTool
```

### Freeze dependenceies in requirements.txt

```
pip freeze > requirements.txt

# Deactivate venv when you're done
deactivate
```

## Deployment

From project root folder (where `serverless.yml` lives), run the following to deploy or update the stack:

```
# Deploy or update a development stack:
serverless deploy --stage dev

# Deploy or update a production stack:
serverless deploy --stage prod
```

## Related repos

Animl is comprised of a number of microservices, most of which are managed in their own repositories.

### Core services

Services necessary to run Animl:

- [Animl Ingest](http://github.com/tnc-ca-geo/animl-ingest)
- [Animl API](http://github.com/tnc-ca-geo/animl-api)
- [Animl Frontend](http://github.com/tnc-ca-geo/animl-frontend)
- [EXIF API](https://github.com/tnc-ca-geo/exif-api)

### Wireless camera services

Services related to ingesting and processing wireless camera trap data:

- [Animl Base](http://github.com/tnc-ca-geo/animl-base)
- [Animl Email Relay](https://github.com/tnc-ca-geo/animl-email-relay)
- [Animl Ingest API](https://github.com/tnc-ca-geo/animl-ingest-api)

### Misc. services

- [Animl ML](http://github.com/tnc-ca-geo/animl-ml)
- [Animl Analytics](http://github.com/tnc-ca-geo/animl-analytics)
