
openjdk:8u121-apline 20Mi/100Mi
```shell
/ # java -XshowSettings:vm -version
VM settings:
    Max. Heap Size (Estimated): 444.69M
    Ergonomics Machine Class: client
    Using VM: OpenJDK 64-Bit Server VM

openjdk version "1.8.0_121"
OpenJDK Runtime Environment (IcedTea 3.3.0) (Alpine 8.121.13-r0)
OpenJDK 64-Bit Server VM (build 25.121-b13, mixed mode)
```

openjdk:8u191-apline 20Mi/100Mi
```shell
/ # java -XshowSettings:vm -version

VM settings:
    Max. Heap Size (Estimated): 48.38M
    Ergonomics Machine Class: client
    Using VM: OpenJDK 64-Bit Server VM

openjdk version "1.8.0_191"
OpenJDK Runtime Environment (IcedTea 3.10.0) (Alpine 8.191.12-r0)
OpenJDK 64-Bit Server VM (build 25.191-b12, mixed mode)

/ # java \
>   -XX:+UnlockExperimentalVMOptions \
>   -XX:+UseCGroupMemoryLimitForHeap \
>   -XshowSettings:vm -version
VM settings:
    Max. Heap Size (Estimated): 48.38M
    Ergonomics Machine Class: client
    Using VM: OpenJDK 64-Bit Server VM

openjdk version "1.8.0_191"
OpenJDK Runtime Environment (IcedTea 3.10.0) (Alpine 8.191.12-r0)
OpenJDK 64-Bit Server VM (build 25.191-b12, mixed mode)
```

openjdk:8u191-apline 20Mi/500Mi
```shell
/ # java \
>   -XX:+UnlockExperimentalVMOptions \
>   -XX:+UseCGroupMemoryLimitForHeap \
>   -XshowSettings:vm -version
VM settings:
    Max. Heap Size (Estimated): 121.81M
    Ergonomics Machine Class: client
    Using VM: OpenJDK 64-Bit Server VM

openjdk version "1.8.0_191"
OpenJDK Runtime Environment (IcedTea 3.10.0) (Alpine 8.191.12-r0)
OpenJDK 64-Bit Server VM (build 25.191-b12, mixed mode)
```

openjdk:8u191-apline 100Mi/500Mi
```shell
/ # java \
>   -XX:+UnlockExperimentalVMOptions \
>   -XX:+UseCGroupMemoryLimitForHeap \
>   -XshowSettings:vm -version
VM settings:
    Max. Heap Size (Estimated): 121.81M
    Ergonomics Machine Class: client
    Using VM: OpenJDK 64-Bit Server VM

openjdk version "1.8.0_191"
OpenJDK Runtime Environment (IcedTea 3.10.0) (Alpine 8.191.12-r0)
OpenJDK 64-Bit Server VM (build 25.191-b12, mixed mode)
```

harbor.guahao-inc.com/jgt/java:1.8_202 20Mi/100Mi
```shell
[root@java-8d9885d46-6gdzh ~]# java -XX:+UnlockExperimentalVMOptions -XX:+UseCGroupMemoryLimitForHeap -XshowSettings:vm -version
VM settings:
    Max. Heap Size (Estimated): 48.38M
    Ergonomics Machine Class: client
    Using VM: Java HotSpot(TM) 64-Bit Server VM

java version "1.8.0_202"
Java(TM) SE Runtime Environment (build 1.8.0_202-b08)
Java HotSpot(TM) 64-Bit Server VM (build 25.202-b08, mixed mode)

[root@java-8d9885d46-6gdzh ~]# java -XshowSettings:vm -version
VM settings:
    Max. Heap Size (Estimated): 48.38M
    Ergonomics Machine Class: client
    Using VM: Java HotSpot(TM) 64-Bit Server VM

java version "1.8.0_202"
Java(TM) SE Runtime Environment (build 1.8.0_202-b08)
Java HotSpot(TM) 64-Bit Server VM (build 25.202-b08, mixed mode)
```