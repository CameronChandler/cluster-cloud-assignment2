Requires:
- ssh-agent setup: eval $(ssh-agent -c) && ssh-add ~/.ssh/id_rsa

- Set up docker context using `docker context create ...` (node-up.py should do this for you)
- Build image using `docker build -t username/repo .`
- Deploy to swarm  using `docker stack deploy -c docker-compose.yaml name-of-deployment`
