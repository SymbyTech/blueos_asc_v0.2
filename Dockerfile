FROM python:3.11

COPY app /app
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install setuptools
RUN pip install -r /app/requirements.txt

# Only install RPi.GPIO if we're on ARM architecture
RUN if [ "$(uname -m)" = "aarch64" ] || [ "$(uname -m)" = "armv7l" ]; then \
    pip install RPi.GPIO; \
    fi

RUN pip install smbus==1.1.post2
RUN ls /app

EXPOSE 80/tcp

LABEL version="0.0.3"

ARG IMAGE_NAME

LABEL permissions='\
{\
  "ExposedPorts": {\
    "80/tcp": {}\
  },\
  "HostConfig": {\
    "Privileged": true,\
    "Binds":["/root/.config:/root/.config", "/dev:/dev"],\
    "Devices": [\
      {\
        "PathOnHost": "/dev/LEDS",\
        "PathInContainer": "/dev/LEDS",\
        "CgroupPermissions": "rwm"\
      },\
      {\
        "PathOnHost": "/dev/MOT1",\
        "PathInContainer": "/dev/MOT1",\
        "CgroupPermissions": "rwm"\
      },\
      {\
        "PathOnHost": "/dev/MOT2",\
        "PathInContainer": "/dev/MOT2",\
        "CgroupPermissions": "rwm"\
      }\
    ],\
    "PortBindings": {\
      "80/tcp": [\
        {\
          "HostPort": ""\
        }\
      ]\
    }\
  }\
}'

ARG AUTHOR
ARG AUTHOR_EMAIL
LABEL authors='[\
    {\
        "name": "$AUTHOR",\
        "email": "$AUTHOR_EMAIL"\
    }\
]'

ARG MAINTAINER
ARG MAINTAINER_EMAIL
LABEL company='{\
        "about": "",\
        "name": "$MAINTAINER",\
        "email": "$MAINTAINER_EMAIL"\
    }'
LABEL type="example"
ARG REPO
ARG OWNER
LABEL readme='https://raw.githubusercontent.com/$OWNER/$REPO/{tag}/README.md'
LABEL links='{\
        "source": "https://github.com/$OWNER/$REPO"\
    }'
LABEL requirements="core >= 1.1"

ENTRYPOINT cd /app && python main.py

