Budil-Zun-Service-Dcoker Image
=======================

By using this dockerfile, you can build your own Zun service docker container eaily and quickly.

Build docker container image
for example, we build a docker container image named `zun-service-img`.
```docker build -t zun-service-img .```

Run zun service container
Start a container by unsing our build image above.
```docker run --name zun-service \
   --net=host \
   -v /var/run:/var/run \
   zun-service-img```


Note: You should enter the container and config the zun config file in the path /etc/zun/,
More info about the config please reference the installation docs.
