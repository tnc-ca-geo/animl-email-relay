ARG TARGETPLATFORM=linux/amd64
FROM --platform=${TARGETPLATFORM} public.ecr.aws/sam/build-python3.9:latest

# Download exiftool and copy its executable and dependencies into
# /output/exiftool/. This image is used as a pip-install sandbox by
# serverless-python-requirements; animl-email-relay ships as a zip-based
# Lambda (see serverless.yml), not a container image.

ENV EXIF_V=13.59

RUN mkdir /output && \
    cd /output && \
    curl -fsSL -o Image-ExifTool-${EXIF_V}.tar.gz "https://cdn.codefornature.org/mirror/Image-ExifTool-${EXIF_V}.tar.gz" && \
    tar -zxf Image-ExifTool-${EXIF_V}.tar.gz && \
    mkdir exiftool && \
    cp Image-ExifTool-${EXIF_V}/exiftool exiftool/ && \
    cp -r Image-ExifTool-${EXIF_V}/lib exiftool/

