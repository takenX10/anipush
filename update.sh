git pull origin main
python3 -m pip install -r requirements.txt
systemctl stop anipush.service
ln -f anipush.service /etc/systemd/system/.
systemctl daemon-reload
systemctl enable anipush.service
systemctl start anipush.service