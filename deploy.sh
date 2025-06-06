
# This script is intended to be used to build all renderer images
# This helps reduce render times since there is no longer a need to rebuild the image
# during render execution
# Another advantage is that, it is able to make use of docker caches hence reducing build time.

cat << 'EOF'

 ▄▄▄▄▄▄▄   ▄▄▄▄▄▄  ▄▄▄▄▄▄▄  ▄        ▄▄▄▄▄▄  ▄         ▄  ▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄
▐░░░░░░░▌ ▐░░░░░░▌▐░░░░░░░▌▐░▌      ▐░░░░░░▌▐░▌       ▐░▌▐░░░░░░░░▌▐░░░░░░░░░▌
▐░█▀▀▀▀█░▌▐░█▀▀▀▀ ▐░█▀▀▀█░▌▐░▌      ▐░█▀▀█░▌▐░▌       ▐░▌▐░█▀▀▀▀▀▀ ▐░█▀▀▀▀▀█░▌
▐░▌    ▐░▌▐░█▄▄▄▄ ▐░█▄▄▄█░▌▐░▌      ▐░▌  ▐░▌▐░█▄▄▄▄▄▄▄█░▌▐░█▄▄▄▄▄▄ ▐░█▄▄▄▄▄█░▌
▐░▌    ▐░▌▐░░░░░░▌▐░░░░░░░▌▐░▌      ▐░▌  ▐░▌▐░░░░░░░░░░░▌▐░░░░░░░░▌▐░░░░░░░░░▌
▐░▌    ▐░▌▐░█▀▀▀▀ ▐░█▀▀▀▀▀ ▐░▌      ▐░▌  ▐░▌ ▀▀▀▀█░█▀▀▀▀ ▐░█▀▀▀▀▀▀ ▐░█▀▀▀█░█▀
▐░█▄▄▄▄█░▌▐░█▄▄▄▄ ▐░▌      ▐░█▄▄▄▄▄ ▐░█▄▄█░▌     ▐░▌     ▐░█▄▄▄▄▄▄ ▐░▌   ▐░▌
▐░░░░░░░▌ ▐░░░░░░▌▐░▌      ▐░░░░░░░▌▐░░░░░░▌     ▐░▌     ▐░░░░░░░░▌▐░▌    ▐░▌

EOF

echo "[ ] Deploying Application"

sudo docker compose up --build -d
echo "[✓] Done deploying Application"
