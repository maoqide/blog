+++ 
draft = false
date = 2024-11-11T17:50:06+08:00
title = "从 harbor 下载指定的镜像层"
description = ""
slug = ""
author = "Maoqide"
tags = ["cloud", "docker"]
categories = []
externalLink = ""
series = []
+++

从 harbor 下载指定的镜像层

<!--more-->
## 场景
业务编译构建的二进制包，需要上传到文件存储服务，然后在发布服务时下载到目标服务器。这里启动服务没有使用容器化部署，而是直接下载二进制包并运行。此时，需要一个文件存储服务，用于存储二进制包，并且需要能够支持访问权限控制、版本维护等，且支持一些自定义的清理策略（如保留最近的几个版本）。

由于目前大部分业务都是容器化部署，有现成的 Harbor 服务，且 Harbor 本身基于镜像天然支持我们上述对存储服务的要求。因此考虑是否可以基于 harbor 镜像做一个文件存储服务，用于存储二进制包。

## 方案
### 实现原理
当我们想要下载 Harbor 镜像的指定层时，实际上是要与 Harbor 背后的 Docker Registry HTTP API V2 交互。

Docker 镜像由多个层组成，每层代表文件系统的一个变化集。这些层是通过内容寻址（content-addressable）的方式存储的，使用 SHA256 哈希值作为标识符。

#### 下载镜像层的流程
##### 1.首先要通过 Harbor 的认证，获取访问 token。

```bash
TOKEN=$(curl -s -u "$USERNAME:$PASSWORD" \
  "https://$HARBOR_URL/service/token?service=harbor-registry&scope=repository:$PROJECT/$IMAGE:pull" \
  | jq -r '.token')
```

##### 2.获取镜像清单
可通过 registey API V2 的 manifest 接口，获取镜像的清单信息。

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.docker.distribution.manifest.v2+json,application/vnd.oci.image.manifest.v1+json" \
  "https://$HARBOR_URL/v2/$PROJECT/$IMAGE/manifests/$TAG"
```

a. 单架构的镜像，返回结果如下：
```json
{
   "schemaVersion": 2,
   "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
   "config": {
      "mediaType": "application/vnd.docker.container.image.v1+json",
      "size": 1147,
      "digest": "sha256:6ef083526b4740ac0868f6fffdcbd3c40fbae98bf83bfdbaab4f7c2ace099c22"
   },
   "layers": [
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 30021731,
         "digest": "sha256:2ecc4ed62a03baf66ce8762672dd349cc02759800a3d9c4ec6d9e3605f487372"
      }
   ]
}
```
可直接从 `layers` 字段中获取镜像层的信息。


b. 多架构镜像的清单可能包含多个平台的信息，返回结果如下：
```json
{
   "schemaVersion": 2,
   "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
   "manifests": [
      {
         "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
         "size": 529,
         "digest": "sha256:dc8ef00adc8be927e83f4b9c168edd4fc881e3f1dcf39016f534e610acd31d52",
         "platform": {
            "architecture": "amd64",
            "os": "linux"
         }
      },
      {
         "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
         "size": 529,
         "digest": "sha256:75caab30dfbe92fbb0bcd7f9411639136c83f67d3edc3452e0d9ae33ad50d43a",
         "platform": {
            "architecture": "arm64",
            "os": "linux"
         }
      }
   ]
}
```

需要再调用 manifest 接口获取指定平台的镜像层信息，即可得到和上面单架构镜像同样的 `layers` 字段。
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
  "$HARBOR_URL/v2/$PROJECT/$IMAGE/manifests/$DIGEST"
```

##### 3.下载指定层
获取到镜像 manifest 的 `layers` 字段口，即可遍历其中的元素，提取出想要的层的 `digest`（SHA256 哈希值）。然后通过 blobs 接口，下载指定的层：
```bash
curl -L -H "Authorization: Bearer $TOKEN" \
  "https://$HARBOR_URL/v2/$PROJECT/$IMAGE/blobs/$LAYER_DIGEST" \
  -o layer.tar.gz
```

通过以上步骤，就可以通过 curl 下载下来我们想要的镜像层的文件，而无需通过 docker 客户端或者下载整个镜像。并且，我们可以很容易的通过文件的 SHA256 哈希值，进行文件的一致性比对。

### 方案设计
了解了基础的技术原理，我们发现的确可以基于 harbor 实现我们的文件存储方案。

首先，文件上传我们仍通过标准的 Docker 镜像方式上传。这样只需要对原有的 CI 流程做很小改动即可。

为了便于查找我们想要的 layer，我们使用 scratch 作为基础镜像，并且 Dockerfile 只做一层 `ADD` 操作，这样镜像的 `layers` 层只会有一层，并且该层下载解压后，就是我们想要的目标文件，没有多余的文件系统或其他文件。

```Dockerfile
FROM scratch
ADD xxx /
```

下载时，通过上面下载镜像层的流程，将镜像唯一的层下载解压即可。一个示例的脚本如下，实际落地时，可选择通过代码集成到我们自己的系统中，并可按需增加下载文件的一致性校验等功能。
```bash
#!/bin/bash

set -e

# 设置变量
HARBOR_URL="https://your-harbor-url"
REPOSITORY="your-project/your-image"
TAG="your-tag"
USERNAME="your-username"
PASSWORD="your-password"
OUTPUT_DIR="layer_contents"
# 指定目标架构，如果不设置则默认为 amd64
TARGET_ARCH=${TARGET_ARCH:-"amd64"}

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 获取访问令牌
get_token() {
    curl -s -u "$USERNAME:$PASSWORD" \
        "$HARBOR_URL/service/token?service=harbor-registry&scope=repository:$REPOSITORY:pull" \
        | jq -r '.token'
}

TOKEN=$(get_token)

# 获取镜像清单
get_manifest() {
    curl -s -H "Authorization: Bearer $TOKEN" \
        -H "Accept: application/vnd.docker.distribution.manifest.v2+json,application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.list.v2+json" \
        "$HARBOR_URL/v2/$REPOSITORY/manifests/$TAG"
}

MANIFEST=$(get_manifest)

# 检查是否为多架构镜像
if [[ $(echo "$MANIFEST" | jq -r '.mediaType') == "application/vnd.docker.distribution.manifest.list.v2+json" ]]; then
    echo "Multi-architecture image detected. Selecting $TARGET_ARCH architecture."
    # 获取指定架构的 digest
    ARCH_DIGEST=$(echo "$MANIFEST" | jq -r '.manifests[] | select(.platform.architecture == "'"$TARGET_ARCH"'") | .digest')

    if [ -z "$ARCH_DIGEST" ]; then
        echo "Error: Architecture $TARGET_ARCH not found in manifest list."
        echo "Available architectures:"
        echo "$MANIFEST" | jq -r '.manifests[].platform.architecture'
        exit 1
    fi

    # 获取该架构的具体清单
    MANIFEST=$(curl -s -H "Authorization: Bearer $TOKEN" \
        -H "Accept: application/vnd.docker.distribution.manifest.v2+json,application/vnd.oci.image.manifest.v1+json" \
        "$HARBOR_URL/v2/$REPOSITORY/manifests/$ARCH_DIGEST")
else
    echo "Single architecture image detected."
fi

# 获取第一层的 digest
LAYER_DIGEST=$(echo "$MANIFEST" | jq -r '.layers[0].digest')

echo "Downloading layer: $LAYER_DIGEST"
LAYER_FILE="$OUTPUT_DIR/layer.tar.gz"

# 下载层
curl -L -H "Authorization: Bearer $TOKEN" \
    "$HARBOR_URL/v2/$REPOSITORY/blobs/$LAYER_DIGEST" \
    -o "$LAYER_FILE"

# 解压层
echo "Extracting layer contents..."
tar -xzf "$LAYER_FILE" -C "$OUTPUT_DIR"

# 删除压缩文件
rm "$LAYER_FILE"

echo "Layer contents have been extracted to $OUTPUT_DIR"
```

## 总结
通过上述方案，我们可以基于 harbor 实现一个文件存储服务，用于存储二进制包。这样我们可以复用的原有的基础设施，减少维护成本。同时，我们也可以通过 harbor 的权限控制、版本维护等功能，更好的管理我们的二进制包。

