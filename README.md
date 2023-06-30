# Run with Docker

    # run with some examples #
    docker run -p 5000:5000 -e USE_EXAMPLE_CONFIG=1

    # run with your own config #
    docker run -p 5000:5000 -v ./config.yaml:/app/config.yaml registry.atlantishq.de/atlantis-hub

    # run with your own config and icon-dir #
    docker run -p 5000:5000 -v ./config.yaml:/app/config.yaml \
                            -v ./static-icons/:/app/static/icons/ \
                            registry.atlantishq.de/atlantis-hub

    # persis database and cache dir #
    docker run -p 5000:5000 -v ./config.yaml:/app/config.yaml \
                            -v ./static-icons/:/app/static/icons/ \
                            -v ./sqlite-instance/:/app/instance/ \
                            -v ./static-cache/:/app/static/cache/ \
                            registry.atlantishq.de/atlantis-hub

You don't *have* to mount the cache directory, but colorthief and downloading icons and images is relatively slow.

# Run with Docker-Compose

    hub:
        image: registry.atlantishq.de/atlantis-hub:latest
        restart: always
        ports:
            - 5000:5000
        volumes:
            - ./config.yaml:/app/config.yaml \
            - ./static-icons/:/app/static/icons/ \
            - ./sqlite-instance/:/app/instance/ \
            - ./static-cache/:/app/static/cache/ \
        environment:
            - USE_EXAMPLE_CONFIG=1

# Config
Config is in yaml format and should look like this:

    tile_A:
        name: Tile_A_Name
        href: https://tile_a_example.com
        background: linear-gradient(90deg, rgb(63 203 87) 20%, rgb(31 110 92) 65%);
        tags:
            - section_name
        groups:
            - oauth_2_group
        auth-type: sso
    
    
    tile_B:
        name: Tile_B_Name
        href: https://tile_b_example.com
        tags:
            - section_name
        groups:
        auth-type: sso

The `background` parameter is optional. If `background` is not set, a color will be determined from the colors of the icon.

The icon is selected in this order:
- `./static/icons` directory contains a picture named `key.png` (i.e. `tile_a.png` or `tile_b.png`).
- `href`-target `og:image`-tag
- `href`-target `rel link icon` field

The first `tag` determines the section the tile will be sorted into.
The `groups` parameter determines which groups an **OAuth**-authenticated client must be part of in order to see this tile. Read next section for more explanation.

# Run behind OAuth2Proxy (or similar)
You can run this project behind any OAuth2 reverse proxy, that supports `X-Forwarded-*` headers, specifically:

    X-Forwarded-Preferred-Username
    X-Forwarded-Groups

In testing you can spin up a nginx container setting those headers without authentication:

    # run in project root
    # add host needed to access the application if it's running natively on your machine
    docker run -p 5001:5001 -v "$(pwd)/nginx-dev-helper/nginx.conf:/etc/nginx/nginx.conf:ro" \
            --add-host host.docker.internal:host-gateway nginx

    # remember to listen on all interfaces when starting the server
    # you might have to restart after the docker network is create if there was none before
    ./server.py -i 0.0.0.0

You can also find debug information hidden in a block at the very bottom of the dashboard.
