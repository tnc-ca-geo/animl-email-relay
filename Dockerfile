FROM public.ecr.aws/sam/build-python3.7:latest

# Download exiftool and copy its executable and dependencies into 
# /output/exiftool/

RUN mkdir /output && \
    cd /output && \
    curl -o Image-ExifTool-13.32.tar.gz https://exiftool.org/Image-ExifTool-13.32.tar.gz && \
    tar -zxf Image-ExifTool-13.32.tar.gz && \
    mkdir exiftool && \
    cp Image-ExifTool-13.32/exiftool exiftool/ && \
    cp -r Image-ExifTool-13.32/lib exiftool/ \
    # sed -i 's/#!\/usr\/bin\/perl -w/#!\/opt\/bin\/perl -w/' ./exiftool/exiftool
    # && sed -i 'Ns/.*/replacement-line/' exiftool/exiftool