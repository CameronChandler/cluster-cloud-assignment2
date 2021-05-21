# Assumes the build context is the root of the project
# Note - Remember to set the 'COUCH_USER' and 'COUCH_PASSWORD'
# environment variables when runninng this container.
from bash
run apk add curl
copy link.bash /
cmd ["bash", "/link.bash"]
