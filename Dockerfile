FROM python:3.8-buster

# apt-get
COPY sources.list /etc/apt/sources.list
RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y locales tzdata && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# locale
RUN echo "en_US.UTF-8 UTF-8\nzh_CN.UTF-8 UTF-8\nzh_CN GB2312\n" >> /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8

# timezone
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN dpkg-reconfigure --frontend noninteractive tzdata

# python
RUN pip config set global.index-url https://mirrors-ssl.aliyuncs.com/pypi/simple && \
    pip install -U pip && \
    pip install fastapi[all] python-jose[cryptography] kubernetes sqlalchemy mysqlclient mkdocs-material jinja2 tenacity loguru hiredis redis pottery && \
    rm -rf /home/dev/.cache

ENV IMAGE_VERSION="brewer-server:1.0"

ENTRYPOINT ["/bin/bash", "-c"]
CMD ["/bin/bash"]

