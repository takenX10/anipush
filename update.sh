source /opt/anipush/venv/bin/activate
git pull origin main
python3 -m pip install -r requirements.txt
systemctl stop anipush.service
cp anipush.service /etc/systemd/system/.
cp aniweb.service /etc/systemd/system/.
systemctl daemon-reload
systemctl stop anipush.service
systemctl enable anipush.service
systemctl start anipush.service
systemctl stop aniweb.service
systemctl enable aniweb.service
systemctl start aniweb.service
