docker-compose build
docker stack deploy -c docker-compose.yaml test
docker build --build-arg http_proxy=http://wwwproxy.unimelb.edu.au:8000 -t comp90024/couch_link couch-link
sleep 15
docker run --network test_couch comp90024/couch_link
